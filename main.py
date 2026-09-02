import os
import sys
from dotenv import load_dotenv

from google import genai
from engine.runner import IaCRunner, LocalStackConnector
from engine.security import CheckovValidator
from engine.state_manager import StateSanitizer
from engine.notifications import SlackNotifier
from engine.logger import get_logger

load_dotenv()

class ShadowPlaneEngine:
    def __init__(self, target_dir: str, pr_number: str):
        self.target_dir = target_dir
        self.pr_number = pr_number
        self.log = get_logger("ShadowPlaneEngine")
        
        self.runner = IaCRunner(binary="tofu", connector=LocalStackConnector())
        self.security = CheckovValidator()
        self.state_manager = StateSanitizer(target_dir)
        self.notifier = SlackNotifier()
        
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required.")
        self.llm_client = genai.Client(api_key=api_key)
        self.model = "gemini-3.7-flash"
        
    def _sanitize_hcl(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"): lines = lines[1:]
            if lines[-1].startswith("```"): lines = lines[:-1]
            text = "\n".join(lines)
        return text

    def run_pipeline(self) -> bool:
        self.log.info(f"========== SHADOWPLANE ENTERPRISE ENGINE ==========")
        self.log.info(f"[1/8] PR Webhook Received: PR #{self.pr_number}")
        
        # 1. Fetch Sanitized State
        self.log.info("[2/8] Fetching and Sanitizing State...")
        has_state = self.state_manager.ingest_and_sanitize()
        if has_state:
            self.log.info("  -> Sanitized tfstate loaded into LocalStack Sandbox.")
        else:
            self.log.info("  -> No existing state found. Proceeding with clean sandbox.")

        try:
            # 2. Tofu Init
            self.log.info("[3/8] Initializing OpenTofu...")
            init_res = self.runner.init(self.target_dir)
            if not init_res["success"]:
                self.log.info(f"Init Failed:\n{init_res['stderr']}")
                return False

            # 3. Tofu Apply (Catch AWS API Error)
            self.log.info("[4/8] Running Tofu Apply (Dry-Run / First Attempt)...")
            apply_res = self.runner.apply(self.target_dir)
            
            original_hcl = ""
            patched_hcl = ""
            main_tf_path = os.path.join(self.target_dir, "main.tf")
            
            if os.path.exists(main_tf_path):
                with open(main_tf_path, "r") as f:
                    original_hcl = f.read()
            
            if apply_res["success"]:
                self.log.info("  -> Apply successful on first try. No AI repair needed.")
                patched_hcl = original_hcl
            else:
                self.log.info(f"  -> Caught AWS API / Provisioning Error (Code {apply_res['exit_code']}).")
                
                # 4. ShadowPatch Patch (with Checkov retry loop)
                self.log.info("[5/8] Engaging ShadowPatch AI & Security Guardrails...")
                
                max_ai_retries = 3
                current_hcl = original_hcl
                patched = False
                error_context = apply_res['stderr']
                
                for attempt in range(1, max_ai_retries + 1):
                    self.log.info(f"  -> [AI Attempt {attempt}] Prompting ShadowPatch Engine...")
                    
                    prompt = f"""
You are an expert AWS OpenTofu/Terraform engineer.
Fix the provided code to resolve the following error:
{error_context}

Original Code:
{current_hcl}

Return ONLY the raw, valid HCL code. No markdown or explanations.
"""
                    try:
                        response = self.llm_client.models.generate_content(
                            model=self.model,
                            contents=prompt
                        )
                        patched_hcl = self._sanitize_hcl(response.text)
                        
                        # Write patch
                        with open(main_tf_path, "w") as f:
                            f.write(patched_hcl)
                            
                        # 5. Checkov Security Scan
                        self.log.info("  -> Running Checkov Security Scan on ShadowPatch Output...")
                        sec_result = self.security.scan(self.target_dir)
                        
                        if sec_result["passed"]:
                            self.log.info("  -> Checkov Validation PASSED. Shift-Left Security enforced.")
                            patched = True
                            break
                        else:
                            self.log.info(f"  -> Checkov Validation FAILED. Issues found: {len(sec_result.get('failed_checks', []))}")
                            error_context = "The previous patch failed Checkov security validation:\n" + str(sec_result["failed_checks"]) + "\nFix the code to be compliant."
                            current_hcl = patched_hcl
                            
                    except Exception as e:
                        self.log.info(f"  -> ShadowPatch Core Error: {e}")
                        break

                if not patched:
                    self.log.info("  -> Failed to generate a secure and valid patch.")
                    return False
                    
                # 6. Tofu Apply in LocalStack (Verification)
                self.log.info("[6/8] Verifying AI Patch with LocalStack OpenTofu Apply...")
                verify_res = self.runner.apply(self.target_dir)
                if not verify_res["success"]:
                    self.log.info(f"  -> Verification Failed!\n{verify_res['stderr']}")
                    return False
                self.log.info("  -> Verification PASSED. Blast Radius Contained.")

            # 7. Slack ChatOps Notification
            self.log.info("[7/8] Dispatching Slack ChatOps Notification...")
            self.notifier.send_verification_success(self.pr_number, original_hcl, patched_hcl)
            
            self.log.info("[8/8] Pipeline Complete. Success.")
            return True
            
        finally:
            self.state_manager.restore_backup()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-dir", default="./demo-infra")
    parser.add_argument("--pr", default="404")
    args = parser.parse_args()
    
    try:
        engine = ShadowPlaneEngine(target_dir=args.target_dir, pr_number=args.pr)
        success = engine.run_pipeline()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
