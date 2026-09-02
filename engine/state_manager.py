import json
import os

class StateSanitizer:
    SENSITIVE_KEYS = ["password", "secret", "private_key", "token", "access_key"]

    def __init__(self, target_dir: str):
        self.target_dir = target_dir
        self.state_file = os.path.join(target_dir, "terraform.tfstate")

    def _sanitize_dict(self, d: dict):
        if not isinstance(d, dict):
            return
        for k, v in list(d.items()):
            if any(sensitive in k.lower() for sensitive in self.SENSITIVE_KEYS):
                d[k] = "REDACTED_BY_SHADOWPLANE"
            elif isinstance(v, dict):
                self._sanitize_dict(v)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        self._sanitize_dict(item)

    def ingest_and_sanitize(self) -> bool:
        """
        Reads existing tfstate, strips sensitive data, and prepares it for the sandbox.
        """
        if not os.path.exists(self.state_file):
            return False
        
        try:
            with open(self.state_file, "r") as f:
                state_data = json.load(f)
            
            # Traverse and strip sensitive data
            for resource in state_data.get("resources", []):
                for instance in resource.get("instances", []):
                    if "attributes" in instance:
                        self._sanitize_dict(instance["attributes"])
                    if "sensitive_attributes" in instance:
                        instance["sensitive_attributes"] = []
                        
            # Write sanitized state
            sanitized_path = os.path.join(self.target_dir, "sanitized_terraform.tfstate")
            with open(sanitized_path, "w") as f:
                json.dump(state_data, f, indent=2)
            
            # Temporarily replace state
            os.rename(self.state_file, self.state_file + ".backup")
            os.rename(sanitized_path, self.state_file)
            
            return True
        except Exception as e:
            print(f"[StateManager] Failed to sanitize state: {e}")
            return False

    def restore_backup(self):
        backup = self.state_file + ".backup"
        if os.path.exists(backup):
            if os.path.exists(self.state_file):
                os.remove(self.state_file)
            os.rename(backup, self.state_file)
