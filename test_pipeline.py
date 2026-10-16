"""
Unit tests for engine/pipeline.py (Option C Verification Pipeline & Change Risk)
"""

import json
import unittest
from unittest.mock import MagicMock
from engine.pipeline import (
    VerificationPipeline,
    VerificationReport,
    VerificationStatus,
    ChangeRiskIntelligence,
)


class TestVerificationPipeline(unittest.TestCase):
    def setUp(self):
        self.mock_runner = MagicMock()
        self.mock_security = MagicMock()
        self.pipeline = VerificationPipeline(
            terraform_dir="./mock_dir",
            runner=self.mock_runner,
            security=self.mock_security,
            commit_sha="abc1234",
        )

    def test_init_failure_stops_pipeline(self):
        """Init failure marks init as FAIL and overall success as False."""
        self.mock_runner.init.return_value = {
            "success": False,
            "stderr": "Initialization error: backend unreachable",
        }

        report = self.pipeline.run()

        self.assertEqual(report.init_result, VerificationStatus.FAIL)
        self.assertIn("backend unreachable", report.init_error)
        self.assertFalse(report.success)
        self.assertTrue(bool(report.evidence_hash))
        # Downstream stages should not have run
        self.mock_security.scan.assert_not_called()
        self.mock_runner.plan.assert_not_called()
        self.mock_runner.apply.assert_not_called()

    def test_security_failure_fails_overall_pipeline(self):
        """Security scan failure marks security as FAIL and overall success as False."""
        self.mock_runner.init.return_value = {"success": True, "stderr": ""}
        self.mock_security.scan.return_value = {
            "passed": False,
            "failed_checks": [{"check_id": "CKV_AWS_18", "check_name": "S3 Bucket Access Logging"}],
        }
        self.mock_runner.plan.return_value = {"success": True, "stdout": "", "stderr": ""}
        self.mock_runner.apply.return_value = {"success": True, "stdout": "Apply complete!", "stderr": ""}

        report = self.pipeline.run()

        self.assertEqual(report.init_result, VerificationStatus.PASS)
        self.assertEqual(report.security_result, VerificationStatus.FAIL)
        self.assertEqual(report.deploy_result, VerificationStatus.PASS)
        self.assertEqual(len(report.security_failures), 1)
        self.assertFalse(report.success)
        self.assertTrue(bool(report.evidence_hash))

    def test_deploy_failure_fails_overall_pipeline(self):
        """Deploy failure marks deploy as FAIL and overall success as False."""
        self.mock_runner.init.return_value = {"success": True, "stderr": ""}
        self.mock_security.scan.return_value = {"passed": True, "failed_checks": []}
        self.mock_runner.plan.return_value = {"success": True, "stdout": "", "stderr": ""}
        self.mock_runner.apply.return_value = {
            "success": False,
            "stdout": "",
            "stderr": "Resource already exists",
        }

        report = self.pipeline.run()

        self.assertEqual(report.init_result, VerificationStatus.PASS)
        self.assertEqual(report.security_result, VerificationStatus.PASS)
        self.assertEqual(report.deploy_result, VerificationStatus.FAIL)
        self.assertIn("Resource already exists", report.deploy_error)
        self.assertFalse(report.success)
        self.assertTrue(bool(report.evidence_hash))

    def test_all_pass_success(self):
        """When init, security, plan, and deploy all succeed with low risk, success is True."""
        self.mock_runner.init.return_value = {"success": True, "stderr": ""}
        self.mock_security.scan.return_value = {"passed": True, "failed_checks": []}
        self.mock_runner.plan.return_value = {"success": True, "stdout": "", "stderr": ""}
        self.mock_runner.apply.return_value = {"success": True, "stdout": "Apply complete: 2 added.", "stderr": ""}

        report = self.pipeline.run()

        self.assertEqual(report.init_result, VerificationStatus.PASS)
        self.assertEqual(report.security_result, VerificationStatus.PASS)
        self.assertEqual(report.plan_result, VerificationStatus.PASS)
        self.assertEqual(report.deploy_result, VerificationStatus.PASS)
        self.assertTrue(report.success)
        self.assertTrue(bool(report.evidence_hash))
        self.assertEqual(report.commit_sha, "abc1234")

    def test_critical_risk_blocks_deployment(self):
        """Destructive action on stateful resource (e.g. S3 deletion) blocks apply."""
        self.mock_runner.init.return_value = {"success": True, "stderr": ""}
        self.mock_security.scan.return_value = {"passed": True, "failed_checks": []}

        # Simulated plan JSON output indicating deletion of an S3 bucket
        mock_plan_event = json.dumps({
            "type": "planned_change",
            "change": {
                "actions": ["delete"],
                "resource": {
                    "resource_type": "aws_s3_bucket",
                    "resource_address": "aws_s3_bucket.prod_data",
                },
            },
        })
        self.mock_runner.plan.return_value = {"success": True, "stdout": mock_plan_event, "stderr": ""}

        report = self.pipeline.run()

        self.assertEqual(report.plan_result, VerificationStatus.PASS)
        self.assertEqual(report.change_risk.risk_score, "CRITICAL")
        self.assertIn("aws_s3_bucket.prod_data", report.change_risk.high_risk_deletions)
        self.assertEqual(report.deploy_result, VerificationStatus.BLOCKED)
        self.assertFalse(report.success)
        # Apply should NOT be invoked when risk is critical
        self.mock_runner.apply.assert_not_called()

    def test_iam_broadening_sets_high_risk(self):
        """Adding or updating IAM policies flags high risk."""
        self.mock_runner.init.return_value = {"success": True, "stderr": ""}
        self.mock_security.scan.return_value = {"passed": True, "failed_checks": []}

        mock_plan_event = json.dumps({
            "type": "planned_change",
            "change": {
                "actions": ["create"],
                "resource": {
                    "resource_type": "aws_iam_policy",
                    "resource_address": "aws_iam_policy.admin_access",
                },
            },
        })
        self.mock_runner.plan.return_value = {"success": True, "stdout": mock_plan_event, "stderr": ""}
        self.mock_runner.apply.return_value = {"success": True, "stdout": "Apply complete.", "stderr": ""}

        report = self.pipeline.run()

        self.assertEqual(report.change_risk.risk_score, "HIGH")
        self.assertIn("aws_iam_policy.admin_access", report.change_risk.iam_broadening)
        # Deploy is not blocked for HIGH (only CRITICAL), but risk is recorded
        self.assertEqual(report.deploy_result, VerificationStatus.PASS)
        self.assertTrue(report.success)

    def test_evidence_hash_determinism(self):
        """Evidence hash must be deterministic for identical report contents."""
        report = VerificationReport(
            timestamp="2026-10-16T12:00:00Z",
            terraform_dir="/tmp/test",
            commit_sha="commit123",
        )
        hash1 = report.compute_evidence_hash()
        hash2 = report.compute_evidence_hash()
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)  # 64-char SHA-256


if __name__ == "__main__":
    unittest.main()
