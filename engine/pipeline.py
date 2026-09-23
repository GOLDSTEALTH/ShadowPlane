"""
engine/pipeline.py — Unified ShadowPlane Verification Pipeline (Option C Implementation)
========================================================================================
Single source of truth for the verification contract.
Implements the core CTO pivot: independent verification evidence with change-risk intelligence.
"""

import os
import time
import hashlib
import json
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, Dict, Any, List

logger = logging.getLogger("ShadowPlane-Pipeline")

class VerificationStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"

@dataclass
class ChangeRiskIntelligence:
    """Change-risk scoring and policy violations detected in the plan phase."""
    high_risk_deletions: List[str] = field(default_factory=list)
    iam_broadening: List[str] = field(default_factory=list)
    risk_score: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL

@dataclass
class VerificationReport:
    """The output contract. Every verification run produces exactly one of these."""
    timestamp: str = ""
    terraform_dir: str = ""
    commit_sha: Optional[str] = None

    # Individual stage results
    init_result: VerificationStatus = VerificationStatus.SKIP
    security_result: VerificationStatus = VerificationStatus.SKIP
    plan_result: VerificationStatus = VerificationStatus.SKIP
    deploy_result: VerificationStatus = VerificationStatus.SKIP
    
    # Change Risk (Option C core feature)
    change_risk: ChangeRiskIntelligence = field(default_factory=ChangeRiskIntelligence)

    # Detail fields
    init_error: str = ""
    security_failures: list = field(default_factory=list)
    deploy_error: str = ""
    deploy_stdout: str = ""

    # Evidence
    evidence_hash: str = ""

    @property
    def success(self) -> bool:
        """Overall pass requires ALL mandatory stages to pass and risk to be acceptable."""
        # Block if critical risk
        if self.change_risk.risk_score == "CRITICAL":
            return False

        return (
            self.init_result == VerificationStatus.PASS
            and self.security_result == VerificationStatus.PASS
            and self.plan_result == VerificationStatus.PASS
            and self.deploy_result == VerificationStatus.PASS
        )

    def compute_evidence_hash(self) -> str:
        """SHA-256 of the report contents for tamper evidence."""
        data = json.dumps(asdict(self), sort_keys=True, default=str)
        self.evidence_hash = hashlib.sha256(data.encode()).hexdigest()
        return self.evidence_hash

    def to_dict(self) -> dict:
        return asdict(self)


class VerificationPipeline:
    """
    Orchestrates: init -> security scan -> plan (risk analysis) -> deploy -> final report.
    """

    def __init__(
        self,
        terraform_dir: str,
        runner,
        security,
        commit_sha: str = None,
    ):
        self.terraform_dir = os.path.abspath(terraform_dir)
        self.runner = runner
        self.security = security
        self.commit_sha = commit_sha

    def _analyze_plan_for_risk(self, plan_stdout: str, report: VerificationReport):
        """Option C: Change-Risk Intelligence. Analyzes the JSON plan output."""
        # The runner.plan outputs JSON lines or a single JSON block depending on TF version.
        # We will parse it to find destructive actions and IAM changes.
        high_risk_resources = ["aws_db_instance", "aws_s3_bucket", "aws_dynamodb_table", "aws_kms_key"]
        
        for line in plan_stdout.splitlines():
            if not line.strip(): continue
            try:
                event = json.loads(line)
                
                # Check for Terraform JSON plan format
                if event.get("type") == "planned_change":
                    change = event.get("change", {})
                    actions = change.get("actions", [])
                    resource_type = change.get("resource", {}).get("resource_type", "")
                    resource_addr = change.get("resource", {}).get("resource_address", "")
                    
                    # Detect Destructive Actions on stateful resources
                    if "delete" in actions and resource_type in high_risk_resources:
                        report.change_risk.high_risk_deletions.append(resource_addr)
                        report.change_risk.risk_score = "CRITICAL"
                        
                    # Detect IAM permission broadening
                    if resource_type in ["aws_iam_policy", "aws_iam_role_policy", "aws_iam_role_policy_attachment"]:
                        if "create" in actions or "update" in actions:
                            report.change_risk.iam_broadening.append(resource_addr)
                            if report.change_risk.risk_score != "CRITICAL":
                                report.change_risk.risk_score = "HIGH"

            except json.JSONDecodeError:
                continue

    def run(self) -> VerificationReport:
        """Execute the full verification pipeline. Returns a VerificationReport."""
        report = VerificationReport(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            terraform_dir=self.terraform_dir,
            commit_sha=self.commit_sha,
        )

        # Stage 1: Init
        logger.info("[1/4] Terraform Init")
        init_res = self.runner.init(self.terraform_dir)
        if not init_res["success"]:
            report.init_result = VerificationStatus.FAIL
            report.init_error = init_res.get("stderr", "")
            report.compute_evidence_hash()
            return report
        report.init_result = VerificationStatus.PASS

        # Stage 2: Security Scan (MANDATORY)
        logger.info("[2/4] Security Scan (pre-apply)")
        sec_result = self.security.scan(self.terraform_dir)
        if not sec_result["passed"]:
            report.security_result = VerificationStatus.FAIL
            report.security_failures = sec_result.get("failed_checks", [])
            # Pipeline continues to plan to gather more evidence, but will fail overall
        else:
            report.security_result = VerificationStatus.PASS

        # Stage 3: Plan & Risk Analysis (Option C)
        logger.info("[3/4] Plan & Risk Analysis")
        plan_res = self.runner.plan(self.terraform_dir)
        if not plan_res["success"]:
            report.plan_result = VerificationStatus.FAIL
            report.deploy_error = plan_res.get("stderr", "")
            report.compute_evidence_hash()
            return report
            
        report.plan_result = VerificationStatus.PASS
        self._analyze_plan_for_risk(plan_res.get("stdout", ""), report)
        
        # Block deploy if critical risk detected
        if report.change_risk.risk_score == "CRITICAL":
            logger.error("[!] CRITICAL risk detected in plan. Blocking deploy.")
            report.deploy_result = VerificationStatus.BLOCKED
            report.deploy_error = "Deploy blocked due to CRITICAL change-risk (e.g., stateful resource deletion)."
            report.compute_evidence_hash()
            return report

        # Stage 4: Deploy to sandbox
        logger.info("[4/4] Sandbox Deploy")
        apply_res = self.runner.apply(self.terraform_dir)
        report.deploy_stdout = apply_res.get("stdout", "")

        if apply_res["success"]:
            report.deploy_result = VerificationStatus.PASS
        else:
            report.deploy_result = VerificationStatus.FAIL
            report.deploy_error = apply_res.get("stderr", "")
            
            # Post-deploy security scan if deploy failed? 
            # (Usually we only rescan if we apply an AI patch, but for Option C we are removing auto-repair from the core loop).

        report.compute_evidence_hash()
        return report
