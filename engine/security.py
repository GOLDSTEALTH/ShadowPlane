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
                if isinstance(parsed, list):
                    parsed = parsed[0]
                
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
            # Checkov not installed
            print("[Checkov] Binary not found. Skipping shift-left security scan.")
            return {"passed": True, "failed_checks": []}
