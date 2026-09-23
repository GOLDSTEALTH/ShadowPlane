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
        
        self.runner = IaCRunner(binary=os.environ.get("SHADOWPLANE_IAC_BINARY", "terraform"), connector=LocalStackConnector())
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
        from engine.pipeline import VerificationPipeline, VerificationReport

        self.log.info(f"========== SHADOWPLANE ENTERPRISE ENGINE ==========")
        self.log.info(f"[1/5] PR Webhook Received: PR #{self.pr_number}")
        
        # 1. Fetch Sanitized State
        self.log.info("[2/5] Fetching and Sanitizing State...")
        has_state = self.state_manager.ingest_and_sanitize()
        if has_state:
            self.log.info("  -> Sanitized tfstate loaded into LocalStack Sandbox.")
        else:
            self.log.info("  -> No existing state found. Proceeding with clean sandbox.")

        try:
            # 2. Run Unified Pipeline (Option C: Init -> Security Scan -> Change-Risk Plan -> Deploy)
            self.log.info("[3/5] Starting Unified Verification Pipeline...")
            
            pipeline = VerificationPipeline(
                terraform_dir=self.target_dir,
                runner=self.runner,
                security=self.security,
                commit_sha=None,  # Placeholder for actual git SHA parsing
            )
            report = pipeline.run()
            
            # Log the report
            self.log.info(f"[4/5] Verification Complete. Evidence Hash: {report.evidence_hash}")
            self.log.info(f"  -> Change Risk Score: {report.change_risk.risk_score}")
            if report.change_risk.high_risk_deletions:
                self.log.warning(f"  -> WARNING: High-risk deletions detected: {report.change_risk.high_risk_deletions}")
            if report.change_risk.iam_broadening:
                self.log.warning(f"  -> WARNING: IAM policy broadening detected: {report.change_risk.iam_broadening}")
            
            # Notify
            self.log.info("[5/5] Dispatching Slack ChatOps Notification...")
            
            # Send notification using the pipeline results
            if report.success:
                # Mock diff since we removed the original vs patched text blocks for now
                self.notifier.send_verification_success(self.pr_number, "Pipeline Execution Passed", f"Evidence Hash: {report.evidence_hash}\nRisk Score: {report.change_risk.risk_score}")
            else:
                self.log.info("Pipeline Failed. Not dispatching success webhook.")
            
            return report.success
            
        finally:
            self.state_manager.restore_backup()


def _cli_entry():
    """Console-script entry point for `shadowplane-engine`."""
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

if __name__ == "__main__":
    _cli_entry()
