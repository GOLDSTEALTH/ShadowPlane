"""
Unit tests for engine/attestation.py (Attestation & Evidence Pack Generator)
"""

import json
import os
import tempfile
import unittest
from engine.pipeline import VerificationReport, VerificationStatus, ChangeRiskIntelligence
from engine.attestation import generate_markdown_attestation, export_attestation_json


class TestAttestationGenerator(unittest.TestCase):
    def test_markdown_attestation_passed(self):
        report = VerificationReport(
            timestamp="2026-10-16T12:00:00Z",
            terraform_dir="/infra",
            commit_sha="abcdef123456",
            init_result=VerificationStatus.PASS,
            security_result=VerificationStatus.PASS,
            plan_result=VerificationStatus.PASS,
            deploy_result=VerificationStatus.PASS,
        )

        md = generate_markdown_attestation(report)

        self.assertIn("PASSED", md)
        self.assertIn("abcdef123456", md)
        self.assertIn("Evidence Hash", md)
        self.assertIn("Pipeline Verification Stages", md)
        self.assertIn("Change-Risk Intelligence", md)

    def test_markdown_attestation_blocked_critical_risk(self):
        report = VerificationReport(
            timestamp="2026-10-16T12:00:00Z",
            terraform_dir="/infra",
            commit_sha="abcdef123456",
            init_result=VerificationStatus.PASS,
            security_result=VerificationStatus.PASS,
            plan_result=VerificationStatus.PASS,
            deploy_result=VerificationStatus.BLOCKED,
            change_risk=ChangeRiskIntelligence(
                high_risk_deletions=["aws_s3_bucket.prod_vault"],
                risk_score="CRITICAL",
            ),
        )

        md = generate_markdown_attestation(report)

        self.assertIn("BLOCKED", md)
        self.assertIn("CRITICAL", md)
        self.assertIn("aws_s3_bucket.prod_vault", md)

    def test_export_attestation_json(self):
        report = VerificationReport(
            timestamp="2026-10-16T12:00:00Z",
            terraform_dir="/infra",
            commit_sha="commit_999",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "attestation.json")
            export_attestation_json(report, out_file)

            self.assertTrue(os.path.exists(out_file))
            with open(out_file, "r") as f:
                data = json.load(f)
            self.assertEqual(data["commit_sha"], "commit_999")
            self.assertTrue(bool(data["evidence_hash"]))


if __name__ == "__main__":
    unittest.main()
