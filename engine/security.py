import subprocess
import json
from typing import Dict, Any

class CheckovValidator:
    def __init__(self, checkov_bin: str = "checkov"):
        self.checkov_bin = checkov_bin

    def scan(self, target_dir: str) -> Dict[str, Any]:
        """
        Runs checkov -d . --output json
        Returns dict with "passed": bool, and "failed_checks": list
        """
        try:
            result = subprocess.run(
                [self.checkov_bin, "-d", ".", "--output", "json"],
                cwd=target_dir,
                capture_output=True,
                text=True
            )
            
            # Checkov returns exit code > 0 if there are failures, but might still output JSON.
            if not result.stdout.strip():
                return {"passed": result.returncode == 0, "failed_checks": [], "raw": result.stderr}

            try:
                parsed = json.loads(result.stdout)
                # Handle multi-framework output: aggregate failures from ALL frameworks
                if isinstance(parsed, list):
                    all_failed = []
                    for framework_result in parsed:
                        all_failed.extend(
                            framework_result.get("results", {}).get("failed_checks", [])
                        )
                    failed_checks = all_failed
                else:
                    failed_checks = parsed.get("results", {}).get("failed_checks", [])
                
                if not failed_checks:
                    return {"passed": True, "failed_checks": []}
                
                simplified_failures = []
                for f in failed_checks:
                    simplified_failures.append({
                        "check_id": f.get("check_id"),
                        "check_name": f.get("check_name"),
                        "resource": f.get("resource"),
                    })
                
                return {"passed": False, "failed_checks": simplified_failures}
            except json.JSONDecodeError:
                return {"passed": False, "failed_checks": [], "raw": result.stdout}

        except FileNotFoundError:
            # Checkov not installed — FAIL CLOSED. Security scanning is mandatory.
            print("[Checkov] ERROR: Binary not found. Security scan BLOCKED (fail-closed).")
            return {"passed": False, "failed_checks": [{"check_id": "SHADOWPLANE_CHECKOV_MISSING", "check_name": "Checkov binary not installed", "resource": "N/A"}]}
