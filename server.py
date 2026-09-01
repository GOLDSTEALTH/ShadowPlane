import json
import logging
import sys
import os
import subprocess
import uuid
import asyncio
import socket
import time
from mcp.server.fastmcp import FastMCP

# Configure logging to write to stderr so it does not interfere with the stdin/stdout communication channel of MCP
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("ShadowPlane-Gateway")

def load_env_file():
    """Lightweight custom parser to load key-value pairs from .env into os.environ."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        logger.info("Loading environment variables from: %s", env_path)
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
                        # Only set if it hasn't been set by host or is default placeholder
                        if key not in os.environ or os.environ[key] == "your_actual_token_here":
                            os.environ[key] = val
        except Exception as e:
            logger.error("Failed to read .env file: %s", e)

# Load .env configuration at module load time
load_env_file()

# Initialize FastMCP server
mcp = FastMCP("ShadowPlane-Gateway")

# Global in-memory log registry
# Maps deployment_id (UUID or normalized directory path) -> record dict
deployment_logs = {}
latest_deployment_id = None

def store_log(deployment_id: str, terraform_dir: str, stdout: str, stderr: str):
    global latest_deployment_id
    record = {
        "deployment_id": deployment_id,
        "terraform_dir": terraform_dir,
        "stdout": stdout,
        "stderr": stderr
    }
    deployment_logs[deployment_id] = record
    norm_dir = os.path.abspath(terraform_dir).replace("\\", "/").lower()
    deployment_logs[norm_dir] = record
    latest_deployment_id = deployment_id
    logger.info("Stored logs for deployment_id: %s (dir: %s)", deployment_id, norm_dir)

def ensure_localstack_sync():
    """Sync helper to check/start LocalStack container."""
    import docker
    client = docker.from_env()
    container_name = "localstack-shadowplane"
    
    # Reload env just in case it was updated during server runtime
    load_env_file()
    
    # Read token from host environment
    auth_token = os.environ.get("LOCALSTACK_AUTH_TOKEN")
    # If the user kept the placeholder, treat it as empty
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
        # Check if environment matches auth token setting
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
        client.containers.run(
            "localstack/localstack:latest",
            name=container_name,
            ports={"4566/tcp": 4566},
            environment=container_env,
            detach=True
        )
        time.sleep(10)

    # Wait up to 30 seconds for the LocalStack port to be ready
    logger.info("Waiting for LocalStack port 4566 to become ready...")
    port_ready = False
    for _ in range(30):
        try:
            with socket.create_connection(("127.0.0.1", 4566), timeout=1):
                logger.info("LocalStack port 4566 is ready!")
                port_ready = True
                break
        except (socket.timeout, ConnectionRefusedError):
            time.sleep(1)
            
    if not port_ready:
        logger.warning("LocalStack port 4566 did not become ready in 30 seconds. Continuing anyway.")

class TerraformExecutor:
    """
    Encapsulates all Terraform execution logic for the ShadowPlane sandbox.

    Responsibilities:
      - Injects LocalStack-targeting environment variables (Prompt 2)
      - Executes `terraform init` and `terraform apply -auto-approve -json` (Prompts 1, 3, 4)
      - Enforces a strict 60-second timeout per subprocess call (Prompt 1)
      - Returns a structured dict: {'success': bool, 'exit_code': int, 'error_log': str,
        'stdout': str, 'errors': list[dict]} (Prompts 1, 4)
    """

    LOCALSTACK_ENDPOINT = "http://127.0.0.1:4566"
    TIMEOUT_SECONDS = 60

    LOCALSTACK_OVERRIDE_TF = """\
provider "aws" {
  access_key                  = "mock"
  secret_key                  = "mock"
  region                      = "us-east-1"
  s3_use_path_style           = true
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    apigateway     = "http://127.0.0.1:4566"
    apigatewayv2   = "http://127.0.0.1:4566"
    autoscaling    = "http://127.0.0.1:4566"
    backup         = "http://127.0.0.1:4566"
    cloudformation = "http://127.0.0.1:4566"
    cloudfront     = "http://127.0.0.1:4566"
    cloudwatch     = "http://127.0.0.1:4566"
    cognitoidp     = "http://127.0.0.1:4566"
    cognitoidentity= "http://127.0.0.1:4566"
    dynamodb       = "http://127.0.0.1:4566"
    ec2            = "http://127.0.0.1:4566"
    elasticache    = "http://127.0.0.1:4566"
    elasticsearch  = "http://127.0.0.1:4566"
    es             = "http://127.0.0.1:4566"
    firehose       = "http://127.0.0.1:4566"
    iam            = "http://127.0.0.1:4566"
    kinesis        = "http://127.0.0.1:4566"
    kms            = "http://127.0.0.1:4566"
    lambda         = "http://127.0.0.1:4566"
    opensearch     = "http://127.0.0.1:4566"
    redshift       = "http://127.0.0.1:4566"
    route53        = "http://127.0.0.1:4566"
    s3             = "http://127.0.0.1:4566"
    s3control      = "http://127.0.0.1:4566"
    sns            = "http://127.0.0.1:4566"
    sqs            = "http://127.0.0.1:4566"
    ssm            = "http://127.0.0.1:4566"
    stepfunctions  = "http://127.0.0.1:4566"
    sts            = "http://127.0.0.1:4566"
  }
}
"""

    def __init__(self, terraform_dir: str, deployment_id: str):
        self.terraform_dir = terraform_dir
        self.deployment_id = deployment_id
        self.override_file = os.path.join(terraform_dir, "localstack_override.tf")

    def _build_env(self) -> dict:
        """Build an environment dict that forces all AWS calls to LocalStack."""
        env = os.environ.copy()
        env["AWS_ACCESS_KEY_ID"] = "mock"
        env["AWS_SECRET_ACCESS_KEY"] = "mock"
        env["AWS_DEFAULT_REGION"] = "us-east-1"
        # Force every AWS SDK / CLI / Terraform provider to target LocalStack
        for svc in ("", "S3", "DYNAMODB", "SQS", "SNS", "LAMBDA",
                    "IAM", "STS", "EC2"):
            key = f"AWS_ENDPOINT_URL_{svc}" if svc else "AWS_ENDPOINT_URL"
            env[key] = self.LOCALSTACK_ENDPOINT
        env["AWS_EC2_METADATA_DISABLED"] = "true"
        return env

    def _write_override(self):
        """Write the LocalStack provider override file into the Terraform dir."""
        with open(self.override_file, "w", encoding="utf-8") as f:
            f.write(self.LOCALSTACK_OVERRIDE_TF)

    def _cleanup_override(self):
        """Remove the temporary override file."""
        if os.path.exists(self.override_file):
            try:
                os.remove(self.override_file)
            except Exception as ex:
                logger.warning("Failed to remove temporary override file: %s", ex)

    @staticmethod
    def _parse_json_errors(raw_output: str) -> list[dict]:
        """
        Parse newline-delimited JSON output from `terraform apply -json`.
        Extracts structured error diagnostics with AWS API error codes.

        Returns a list of dicts, each containing:
          - type: the Terraform log level (e.g., "diagnostic")
          - severity: "error" | "warning"
          - summary: short error description
          - detail: full error detail string
          - resource: the Terraform resource address (if available)
        """
        errors = []
        for line in raw_output.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Terraform JSON output uses @level and @message at the top level,
            # and nests diagnostic info under "diagnostic" for errors.
            if entry.get("type") == "diagnostic":
                diag = entry.get("diagnostic", {})
                if diag.get("severity") == "error":
                    errors.append({
                        "type": "diagnostic",
                        "severity": "error",
                        "summary": diag.get("summary", ""),
                        "detail": diag.get("detail", ""),
                        "resource": diag.get("address", ""),
                    })
            elif entry.get("@level") == "error":
                errors.append({
                    "type": "message",
                    "severity": "error",
                    "summary": entry.get("@message", ""),
                    "detail": entry.get("@message", ""),
                    "resource": "",
                })
        return errors

    def execute(self) -> dict:
        """
        Run `terraform init` then `terraform apply -auto-approve -json`.

        Returns:
            dict: {
                'success':   bool  — True if apply exited 0,
                'exit_code': int   — process return code (or -1 on timeout),
                'error_log': str   — raw stderr / error text,
                'stdout':    str   — raw stdout,
                'errors':    list  — parsed JSON error diagnostics,
            }
        """
        # Ensure LocalStack is up
        ensure_localstack_sync()

        env = self._build_env()
        self._write_override()

        try:
            # ── terraform init ────────────────────────────────────────────
            logger.info("Running 'terraform init' in %s", self.terraform_dir)
            init_res = subprocess.run(
                ["terraform", "init"],
                cwd=self.terraform_dir,
                capture_output=True,
                text=True,
                env=env,
                timeout=self.TIMEOUT_SECONDS,
                check=True,
            )

            # ── terraform apply -auto-approve -json ───────────────────────
            logger.info("Running 'terraform apply -auto-approve -json' in %s", self.terraform_dir)
            apply_res = subprocess.run(
                ["terraform", "apply", "-auto-approve", "-json"],
                cwd=self.terraform_dir,
                capture_output=True,
                text=True,
                env=env,
                timeout=self.TIMEOUT_SECONDS,
            )

            parsed_errors = self._parse_json_errors(apply_res.stdout)

            if apply_res.returncode != 0:
                error_log = apply_res.stderr or apply_res.stdout
                # Also build a human-readable summary from JSON diagnostics
                if parsed_errors:
                    error_summary = "\n".join(
                        f"{e['summary']}: {e['detail']}" for e in parsed_errors
                    )
                    error_log = error_summary

                logger.error(
                    "Terraform apply failed: returncode=%d, errors=%d",
                    apply_res.returncode, len(parsed_errors),
                )
                store_log(
                    self.deployment_id, self.terraform_dir,
                    apply_res.stdout, error_log,
                )
                return {
                    "success": False,
                    "exit_code": apply_res.returncode,
                    "error_log": error_log,
                    "stdout": apply_res.stdout,
                    "errors": parsed_errors,
                }

            # Success path
            store_log(self.deployment_id, self.terraform_dir, apply_res.stdout, "")
            return {
                "success": True,
                "exit_code": 0,
                "error_log": "",
                "stdout": apply_res.stdout,
                "errors": [],
            }

        except subprocess.TimeoutExpired as te:
            error_msg = (
                f"Terraform command timed out after {self.TIMEOUT_SECONDS}s: {te.cmd}"
            )
            logger.error(error_msg)
            store_log(self.deployment_id, self.terraform_dir, "", error_msg)
            return {
                "success": False,
                "exit_code": -1,
                "error_log": error_msg,
                "stdout": "",
                "errors": [{"type": "timeout", "severity": "error",
                            "summary": "Execution timed out",
                            "detail": error_msg, "resource": ""}],
            }

        except subprocess.CalledProcessError as e:
            # This catches `terraform init` failures (check=True)
            logger.error(
                "Terraform execution failed: command=%s returncode=%d", e.cmd, e.returncode
            )
            stderr_val = e.stderr or f"Terraform command {e.cmd} failed with exit code {e.returncode}"
            store_log(self.deployment_id, self.terraform_dir, e.stdout or "", stderr_val)
            return {
                "success": False,
                "exit_code": e.returncode,
                "error_log": stderr_val,
                "stdout": e.stdout or "",
                "errors": [{"type": "process_error", "severity": "error",
                            "summary": f"Command failed: {e.cmd}",
                            "detail": stderr_val, "resource": ""}],
            }

        except Exception as ex:
            error_msg = f"Unexpected error during Terraform execution: {ex}"
            logger.error(error_msg)
            store_log(self.deployment_id, self.terraform_dir, "", error_msg)
            return {
                "success": False,
                "exit_code": -1,
                "error_log": error_msg,
                "stdout": "",
                "errors": [{"type": "exception", "severity": "error",
                            "summary": type(ex).__name__,
                            "detail": error_msg, "resource": ""}],
            }

        finally:
            self._cleanup_override()


def run_terraform_deploy_sync(terraform_dir: str, deployment_id: str) -> str:
    """
    Legacy sync wrapper — delegates to TerraformExecutor.
    Preserves backward compatibility with clone_and_deploy MCP tool.
    Raises RuntimeError on failure (as before).
    """
    executor = TerraformExecutor(terraform_dir, deployment_id)
    result = executor.execute()
    if result["success"]:
        return result["stdout"]
    raise RuntimeError(f"Terraform execution failed: {result['error_log']}")

@mcp.tool()
async def clone_and_deploy(terraform_dir: str) -> str:
    """Clone and deploy Terraform configuration files from the specified directory.

    Args:
        terraform_dir: Path to the directory containing Terraform files.
    """
    logger.info("clone_and_deploy tool invoked with path: %s", terraform_dir)
    deployment_id = str(uuid.uuid4())
    logger.info("Generated deployment ID: %s", deployment_id)
    
    # Run the blocking logic in a separate thread to avoid blocking the asyncio event loop
    stdout = await asyncio.to_thread(run_terraform_deploy_sync, terraform_dir, deployment_id)
    return stdout

@mcp.tool()
async def read_sandbox_logs(deployment_id: str) -> str:
    """Read logs for a sandbox deployment using its deployment ID.

    Args:
        deployment_id: The unique identifier or directory path of the sandbox deployment.
    """
    logger.info("read_sandbox_logs tool invoked with ID: %s", deployment_id)
    
    id_to_lookup = deployment_id
    # If special keyword or empty, lookup latest
    if not id_to_lookup or id_to_lookup.lower() in ("latest", "current", ""):
        id_to_lookup = latest_deployment_id
        
    if not id_to_lookup:
        return "No deployments have been run yet."
        
    # Lookup by deployment_id or directory key
    record = deployment_logs.get(id_to_lookup)
    if not record:
        norm_dir = os.path.abspath(id_to_lookup).replace("\\", "/").lower()
        record = deployment_logs.get(norm_dir)
        
    if not record:
        return f"No logs found for deployment ID or directory: {deployment_id}"
        
    # Return stderr if it exists, otherwise stdout
    if record["stderr"]:
        return record["stderr"]
    return record["stdout"]

if __name__ == "__main__":
    logger.info("Starting ShadowPlane-Gateway MCP server")
    mcp.run()
