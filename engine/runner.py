import subprocess
import os
import sys
import logging
import time
import socket
from abc import ABC, abstractmethod
from typing import Dict, Any

# Add parent directory to path so we can import circuit_breaker
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from circuit_breaker import circuit_breaker, SYSTEM_OVERRIDE_MESSAGE
from engine.constants import LOCALSTACK_SERVICES

logger = logging.getLogger("ShadoPlane-Runner")


def _load_env_file():
    """Lightweight custom parser to load key-value pairs from root .env into os.environ."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(project_root, ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip("'\"")
                        if key not in os.environ or os.environ[key] == "your_actual_token_here":
                            os.environ[key] = val
        except Exception as e:
            logger.error("Failed to read .env file: %s", e)


def ensure_localstack_sync():
    """Sync helper to check/start LocalStack container."""
    try:
        import docker
    except ImportError:
        logger.warning("docker python library not installed — skipping LocalStack auto-start.")
        return

    try:
        client = docker.from_env()
        client.ping()
    except Exception as e:
        logger.warning("Docker daemon is not available (%s) — skipping LocalStack auto-start.", e)
        return

    container_name = "localstack-shadowplane"
    _load_env_file()

    auth_token = os.environ.get("LOCALSTACK_AUTH_TOKEN")
    if auth_token == "your_actual_token_here":
        auth_token = None

    container_env = {}
    if auth_token:
        container_env["LOCALSTACK_AUTH_TOKEN"] = auth_token
        container_env["ACTIVATE_PRO"] = "1"
        logger.info("LocalStack Auth Token found in environment. Activating Pro mode.")

    logger.info("Checking LocalStack container status...")
    recreate = False
    try:
        container = client.containers.get(container_name)
        env_vars = container.attrs.get("Config", {}).get("Env", [])
        has_token_in_container = any(e.startswith("LOCALSTACK_AUTH_TOKEN=") for e in env_vars)

        if auth_token and not has_token_in_container:
            logger.info("Existing container does not have LOCALSTACK_AUTH_TOKEN set. Recreating...")
            recreate = True
        elif not auth_token and has_token_in_container:
            logger.info("Existing container has LOCALSTACK_AUTH_TOKEN set, but none in host. Recreating...")
            recreate = True

        if recreate:
            logger.info("Stopping and removing container '%s' to recreate it", container_name)
            try:
                container.stop(timeout=5)
            except Exception:
                pass
            container.remove()
            raise docker.errors.NotFound("Recreating container")

        logger.info("Found existing container '%s' with status: %s", container_name, container.status)
        if container.status != "running":
            logger.info("Starting stopped container '%s'", container_name)
            container.start()
            time.sleep(5)
    except docker.errors.NotFound:
        logger.info("Container '%s' not found or recreating. Starting a new one...", container_name)
        try:
            client.containers.run(
                "localstack/localstack:latest",
                name=container_name,
                ports={"4566/tcp": 4566},
                environment=container_env,
                detach=True,
            )
            time.sleep(10)
        except Exception as e:
            logger.warning("Failed to launch LocalStack container: %s", e)
            return
    except Exception as e:
        logger.warning("Error checking LocalStack container: %s", e)
        return

    logger.info("Waiting for LocalStack port 4566 to become ready...")
    port_ready = False
    for _ in range(30):
        try:
            with socket.create_connection(("127.0.0.1", 4566), timeout=1):
                logger.info("LocalStack port 4566 is ready!")
                port_ready = True
                break
        except (socket.timeout, ConnectionRefusedError, OSError):
            time.sleep(1)

    if not port_ready:
        logger.warning("LocalStack port 4566 did not become ready in 30 seconds. Continuing anyway.")


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

from engine.constants import LOCALSTACK_SERVICES

class LocalStackConnector(EmulatorConnector):
    def get_env_vars(self) -> Dict[str, str]:
        endpoint = os.getenv("AWS_ENDPOINT_URL", "http://127.0.0.1:4566")
        env = {
            "AWS_ACCESS_KEY_ID": "test",
            "AWS_SECRET_ACCESS_KEY": "test",
            "AWS_DEFAULT_REGION": "us-east-1",
            "AWS_ENDPOINT_URL": endpoint,
            "AWS_EC2_METADATA_DISABLED": "true",
        }
        for svc in ("S3", "DYNAMODB", "SQS", "SNS", "LAMBDA", "IAM", "STS", "EC2"):
            env[f"AWS_ENDPOINT_URL_{svc}"] = endpoint
        return env
    
    def setup_overrides(self, target_dir: str):
        endpoint = os.getenv("AWS_ENDPOINT_URL", "http://127.0.0.1:4566")
        endpoints_block = "\n".join(
            f'    {svc:<18} = "{endpoint}"' for svc in LOCALSTACK_SERVICES
        )
        override_hcl = f"""
provider "aws" {{
  access_key                  = "test"
  secret_key                  = "test"
  region                      = "us-east-1"
  s3_use_path_style           = true
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  endpoints {{
{endpoints_block}
  }}
}}
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
            out = e.stdout.decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
            err = e.stderr.decode(errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
            return {
                "success": False,
                "exit_code": 124,
                "stdout": out,
                "stderr": f"Command timed out after {e.timeout}s: {err}".strip()
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
        # ── Circuit Breaker: pre-check ────────────────────────────────────
        if circuit_breaker.is_tripped(target_dir):
            status = circuit_breaker.get_status(target_dir)
            return {
                "success": False,
                "exit_code": -2,
                "stdout": "",
                "stderr": SYSTEM_OVERRIDE_MESSAGE.format(
                    failure_count=status["failure_count"],
                    terraform_dir=target_dir,
                    window=status["window_seconds"],
                ),
            }

        self.connector.setup_overrides(target_dir)
        try:
            result = self._run([self.binary, "apply", "-auto-approve", "-json"], target_dir)
        finally:
            self.connector.cleanup_overrides(target_dir)

        # ── Circuit Breaker: post-check ───────────────────────────────────
        if result["success"]:
            circuit_breaker.record_success(target_dir)
        else:
            tripped = circuit_breaker.check_and_record_failure(target_dir)
            if tripped:
                result["stderr"] = SYSTEM_OVERRIDE_MESSAGE.format(
                    failure_count=circuit_breaker.get_status(target_dir)["failure_count"],
                    terraform_dir=target_dir,
                    window=circuit_breaker.get_status(target_dir)["window_seconds"],
                )
        return result
