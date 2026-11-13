"""
Unit tests for engine/docker_runner.py (Isolated Container Runner)
"""

import unittest
from unittest.mock import MagicMock, patch
from engine.docker_runner import DockerIaCRunner
from engine.runner import LocalStackConnector


class TestDockerIaCRunner(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.mock_connector = MagicMock(spec=LocalStackConnector)
        self.runner = DockerIaCRunner(
            image="hashicorp/terraform:1.7",
            connector=self.mock_connector,
            client=self.mock_client,
        )

    def test_is_available_when_ping_succeeds(self):
        self.mock_client.ping.return_value = True
        self.assertTrue(self.runner.is_available)

    def test_is_available_false_when_ping_fails(self):
        self.mock_client.ping.side_effect = Exception("Docker daemon down")
        self.assertFalse(self.runner.is_available)

    def test_environment_strips_host_credentials(self):
        """Sanitized container env must have mock credentials and local endpoint."""
        env = self.runner._build_container_env()
        self.assertEqual(env["AWS_ACCESS_KEY_ID"], "test")
        self.assertEqual(env["AWS_SECRET_ACCESS_KEY"], "test")
        self.assertEqual(env["AWS_DEFAULT_REGION"], "us-east-1")
        self.assertEqual(env["TF_IN_AUTOMATION"], "1")
        self.assertIn("AWS_ENDPOINT_URL", env)

    def test_run_container_success(self):
        """Successful container run returns exit_code 0, stdout from separated logs, and verifies cap_drop."""
        self.mock_client.ping.return_value = True
        mock_container = MagicMock()
        mock_container.wait.return_value = {"StatusCode": 0}
        
        def logs_dispatch(stdout=True, stderr=True):
            if stdout and not stderr:
                return b"Terraform initialized successfully!"
            return b""
        mock_container.logs.side_effect = logs_dispatch
        self.mock_client.containers.create.return_value = mock_container

        res = self.runner.init("./mock_infra")

        self.assertTrue(res["success"])
        self.assertEqual(res["exit_code"], 0)
        self.assertIn("Terraform initialized", res["stdout"])
        self.assertEqual(res["stderr"], "")
        mock_container.remove.assert_called_with(force=True)

        # Verify hardened container creation settings
        create_kwargs = self.mock_client.containers.create.call_args.kwargs
        self.assertEqual(create_kwargs.get("cap_drop"), ["ALL"])
        self.assertEqual(create_kwargs.get("security_opt"), ["no-new-privileges:true"])

        # Verify separated container.logs calls
        self.assertIn((( ), {"stdout": True, "stderr": False}), mock_container.logs.call_args_list)
        self.assertIn((( ), {"stdout": False, "stderr": True}), mock_container.logs.call_args_list)

    def test_run_container_failure(self):
        """Non-zero exit code returns success=False and separated stderr."""
        self.mock_client.ping.return_value = True
        mock_container = MagicMock()
        mock_container.wait.return_value = {"StatusCode": 1}
        
        def logs_dispatch(stdout=True, stderr=True):
            if stderr and not stdout:
                return b"Error: Configuration invalid"
            return b""
        mock_container.logs.side_effect = logs_dispatch
        self.mock_client.containers.create.return_value = mock_container

        res = self.runner.init("./mock_infra")

        self.assertFalse(res["success"])
        self.assertEqual(res["exit_code"], 1)
        self.assertIn("Configuration invalid", res["stderr"])

        # Verify separated logs calls
        self.assertIn((( ), {"stdout": True, "stderr": False}), mock_container.logs.call_args_list)
        self.assertIn((( ), {"stdout": False, "stderr": True}), mock_container.logs.call_args_list)

    def test_run_container_failure_stderr_fallback_to_stdout(self):
        """When stderr is empty on non-zero exit, fallback to stdout."""
        self.mock_client.ping.return_value = True
        mock_container = MagicMock()
        mock_container.wait.return_value = {"StatusCode": 1}
        
        def logs_dispatch(stdout=True, stderr=True):
            if stdout and not stderr:
                return b"Fatal output in stdout stream"
            return b""
        mock_container.logs.side_effect = logs_dispatch
        self.mock_client.containers.create.return_value = mock_container

        res = self.runner.init("./mock_infra")

        self.assertFalse(res["success"])
        self.assertEqual(res["exit_code"], 1)
        self.assertIn("Fatal output in stdout stream", res["stderr"])

    @patch("engine.docker_runner.circuit_breaker")
    def test_apply_blocked_by_circuit_breaker(self, mock_cb):
        """Apply must be blocked immediately if circuit breaker is tripped."""
        mock_cb.is_tripped.return_value = True
        mock_cb.get_status.return_value = {"failure_count": 4, "window_seconds": 300}

        res = self.runner.apply("./mock_infra")

        self.assertFalse(res["success"])
        self.assertEqual(res["exit_code"], -2)
        self.assertIn("TRIPPED", res["stderr"])
        self.mock_client.containers.create.assert_not_called()


if __name__ == "__main__":
    unittest.main()
