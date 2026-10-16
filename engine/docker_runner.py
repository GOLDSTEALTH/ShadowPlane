"""
engine/docker_runner.py - Hardened Docker Container Sandbox Runner
===================================================================
Executes Terraform/OpenTofu inside an isolated, disposable Docker container
rather than directly on the host operating system.

Security controls:
- Strips host environment variables (no host AWS keys, SSH credentials, or tokens).
- Mounts target directory into an isolated container workspace (/workspace).
- Restricts container resources (memory, CPU).
- Redirects AWS API endpoints exclusively to LocalStack (via host.docker.internal).
- Mitigates host breakout risks from `local-exec` provisioners.
"""

import os
import sys
import logging
from typing import Dict, Any, Optional
import docker
from docker.errors import DockerException, ContainerError, ImageNotFound

# Add parent directory for circuit_breaker
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from circuit_breaker import circuit_breaker, SYSTEM_OVERRIDE_MESSAGE
from engine.constants import LOCALSTACK_SERVICES
from engine.runner import EmulatorConnector, LocalStackConnector

logger = logging.getLogger("ShadowPlane-DockerRunner")


class DockerIaCRunner:
    """
    Executes IaC operations inside an isolated Docker sandbox container.
    Provides the same interface as IaCRunner (init, plan, apply).
    """

    DEFAULT_IMAGE = "hashicorp/terraform:1.7"
    WORKSPACE_DIR = "/workspace"

    def __init__(
        self,
        image: Optional[str] = None,
        connector: Optional[EmulatorConnector] = None,
        client: Optional[docker.DockerClient] = None,
        timeout: int = 120,
    ):
        self.image = image or os.environ.get("SHADOWPLANE_SANDBOX_IMAGE", self.DEFAULT_IMAGE)
        self.connector = connector or LocalStackConnector()
        self.timeout = timeout
        
        try:
            self.client = client or docker.from_env()
            self._docker_available = True
        except DockerException as e:
            logger.warning("Docker daemon not reachable: %s", e)
            self.client = None
            self._docker_available = False

    @property
    def is_available(self) -> bool:
        """Returns True if Docker daemon is accessible."""
        if not self._docker_available or not self.client:
            return False
        try:
            return self.client.ping()
        except Exception:
            return False

    def _build_container_env(self) -> Dict[str, str]:
        """
        Builds a sanitized environment dict for the container.
        Explicitly isolates the container from host AWS credentials.
        """
        # Base mock AWS credentials
        endpoint = os.environ.get("LOCALSTACK_DOCKER_ENDPOINT", "http://host.docker.internal:4566")
        env = {
            "AWS_ACCESS_KEY_ID": "test",
            "AWS_SECRET_ACCESS_KEY": "test",
            "AWS_DEFAULT_REGION": "us-east-1",
            "AWS_ENDPOINT_URL": endpoint,
            "AWS_EC2_METADATA_DISABLED": "true",
            "TF_IN_AUTOMATION": "1",
            "TF_INPUT": "0",
        }
        for svc in ("S3", "DYNAMODB", "SQS", "SNS", "LAMBDA", "IAM", "STS", "EC2"):
            env[f"AWS_ENDPOINT_URL_{svc}"] = endpoint
        return env

    def _run_container(self, cmd: list, target_dir: str) -> Dict[str, Any]:
        """Runs a command inside an ephemeral container and collects output."""
        if not self.is_available:
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": "Docker daemon is not available or unreachable.",
            }

        abs_target_dir = os.path.abspath(target_dir)
        container_env = self._build_container_env()

        # Mount target directory into /workspace
        volumes = {
            abs_target_dir: {
                "bind": self.WORKSPACE_DIR,
                "mode": "rw",
            }
        }

        # Extra hosts to resolve host machine where LocalStack is exposed
        extra_hosts = {"host.docker.internal": "host-gateway"}

        try:
            # Ensure sandbox image is present
            try:
                self.client.images.get(self.image)
            except ImageNotFound:
                logger.info("Pulling sandbox image '%s'...", self.image)
                self.client.images.pull(self.image)

            container = self.client.containers.create(
                image=self.image,
                command=cmd,
                working_dir=self.WORKSPACE_DIR,
                environment=container_env,
                volumes=volumes,
                extra_hosts=extra_hosts,
                network_mode="bridge",
                mem_limit="1024m",
                nano_cpus=2_000_000_000,  # 2 CPUs
            )

            try:
                container.start()
                res = container.wait(timeout=self.timeout)
                exit_code = res.get("StatusCode", 0)
                logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")

                stdout = logs if exit_code == 0 else ""
                stderr = logs if exit_code != 0 else ""

                return {
                    "success": exit_code == 0,
                    "exit_code": exit_code,
                    "stdout": stdout,
                    "stderr": stderr,
                }
            finally:
                try:
                    container.remove(force=True)
                except Exception:
                    pass

        except ContainerError as ce:
            return {
                "success": False,
                "exit_code": ce.exit_status,
                "stdout": "",
                "stderr": str(ce),
            }
        except Exception as e:
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Docker runner execution error: {e}",
            }

    def init(self, target_dir: str) -> Dict[str, Any]:
        """Executes 'terraform init' in the sandbox container."""
        return self._run_container(["terraform", "init"], target_dir)

    def plan(self, target_dir: str) -> Dict[str, Any]:
        """Executes 'terraform plan -json' in the sandbox container."""
        self.connector.setup_overrides(target_dir)
        try:
            return self._run_container(["terraform", "plan", "-json"], target_dir)
        finally:
            self.connector.cleanup_overrides(target_dir)

    def apply(self, target_dir: str) -> Dict[str, Any]:
        """Executes 'terraform apply -auto-approve -json' with circuit breaker safety."""
        # Circuit Breaker pre-check
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
            result = self._run_container(
                ["terraform", "apply", "-auto-approve", "-json"],
                target_dir,
            )
        finally:
            self.connector.cleanup_overrides(target_dir)

        # Circuit Breaker post-check
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
