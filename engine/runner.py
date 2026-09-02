import subprocess
import os
from abc import ABC, abstractmethod
from typing import Dict, Any

class EmulatorConnector(ABC):
    @abstractmethod
    def get_env_vars(self) -> Dict[str, str]:
        pass

    @abstractmethod
    def setup_overrides(self, target_dir: str):
        pass

    @abstractmethod
    def cleanup_overrides(self, target_dir: str):
        pass

class LocalStackConnector(EmulatorConnector):
    def get_env_vars(self) -> Dict[str, str]:
        return {
            "AWS_ACCESS_KEY_ID": "test",
            "AWS_SECRET_ACCESS_KEY": "test",
            "AWS_DEFAULT_REGION": "us-east-1",
        }
    
    def setup_overrides(self, target_dir: str):
        override_hcl = """
provider "aws" {
  access_key                  = "test"
  secret_key                  = "test"
  region                      = "us-east-1"
  s3_use_path_style           = true
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  endpoints {
    s3       = "http://127.0.0.1:4566"
    dynamodb = "http://127.0.0.1:4566"
    iam      = "http://127.0.0.1:4566"
    sts      = "http://127.0.0.1:4566"
    ec2      = "http://127.0.0.1:4566"
  }
}
"""
        with open(os.path.join(target_dir, "localstack_override_providers.tf"), "w") as f:
            f.write(override_hcl)

    def cleanup_overrides(self, target_dir: str):
        override_path = os.path.join(target_dir, "localstack_override_providers.tf")
        if os.path.exists(override_path):
            os.remove(override_path)

class AzuriteConnector(EmulatorConnector):
    """
    Placeholder for Azure Storage Emulator (Azurite) support.
    """
    def get_env_vars(self) -> Dict[str, str]:
        return {"ARM_USE_AZUREAD": "false"}
    
    def setup_overrides(self, target_dir: str):
        pass

    def cleanup_overrides(self, target_dir: str):
        pass

class IaCRunner:
    def __init__(self, binary: str = "tofu", connector: EmulatorConnector = None):
        self.binary = binary
        self.connector = connector or LocalStackConnector()

    def _run(self, cmd: list, target_dir: str) -> Dict[str, Any]:
        env = os.environ.copy()
        env.update(self.connector.get_env_vars())
        
        try:
            result = subprocess.run(
                cmd,
                cwd=target_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=60
            )
            return {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except subprocess.TimeoutExpired as e:
            return {
                "success": False,
                "exit_code": 124,
                "stdout": e.stdout.decode() if e.stdout else "",
                "stderr": f"Command timed out after {e.timeout}s"
            }

    def init(self, target_dir: str) -> Dict[str, Any]:
        return self._run([self.binary, "init"], target_dir)

    def plan(self, target_dir: str) -> Dict[str, Any]:
        self.connector.setup_overrides(target_dir)
        try:
            return self._run([self.binary, "plan", "-json"], target_dir)
        finally:
            self.connector.cleanup_overrides(target_dir)

    def apply(self, target_dir: str) -> Dict[str, Any]:
        self.connector.setup_overrides(target_dir)
        try:
            return self._run([self.binary, "apply", "-auto-approve", "-json"], target_dir)
        finally:
            self.connector.cleanup_overrides(target_dir)
