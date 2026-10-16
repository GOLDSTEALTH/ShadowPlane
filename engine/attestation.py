"""
engine/attestation.py - Verification Attestation & Evidence Pack Generator
===========================================================================
Generates cryptographic and human-readable attestation artifacts for pull
requests, CI gates, and compliance audits.
"""

import json
from typing import Optional
from engine.pipeline import VerificationReport, VerificationStatus


def generate_markdown_attestation(report: VerificationReport) -> str:
    """
    Renders a GitHub-Flavored Markdown attestation card from a VerificationReport.
    Suitable for PR comments, CI step summaries, and terminal outputs.
    """
    if report.success:
        badge = "🟢 **PASSED**"
        title = "ShadowPlane Verification Attestation: PASSED"
    elif report.deploy_result == VerificationStatus.BLOCKED or report.change_risk.risk_score == "CRITICAL":
        badge = "⛔ **BLOCKED (CRITICAL CHANGE RISK)**"
        title = "ShadowPlane Verification Attestation: BLOCKED"
    else:
        badge = "🔴 **FAILED**"
        title = "ShadowPlane Verification Attestation: FAILED"

    commit_display = f"`{report.commit_sha}`" if report.commit_sha else "_Not provided_"
    evidence_hash = report.evidence_hash or report.compute_evidence_hash()

    md = [
        f"## 🛡️ {title}",
        "",
        f"**Gate Status**: {badge}  ",
        f"**Evidence Hash**: `{evidence_hash}`  ",
        f"**Target Directory**: `{report.terraform_dir}`  ",
        f"**Commit SHA**: {commit_display}  ",
        f"**Timestamp**: `{report.timestamp}`  ",
        "",
        "### Pipeline Verification Stages",
        "",
        "| Stage | Result | Notes |",
        "|---|---|---|",
        f"| **1. Terraform Init** | `{report.init_result.value.upper()}` | {'Initialized successfully' if report.init_result == VerificationStatus.PASS else report.init_error[:100]} |",
        f"| **2. Fail-Closed Security (Checkov)** | `{report.security_result.value.upper()}` | {len(report.security_failures)} failed checks |",
        f"| **3. Plan & Change-Risk** | `{report.plan_result.value.upper()}` | Risk Level: **{report.change_risk.risk_score}** |",
        f"| **4. Sandbox Deploy (LocalStack)** | `{report.deploy_result.value.upper()}` | {'Apply succeeded' if report.deploy_result == VerificationStatus.PASS else report.deploy_error[:100]} |",
        "",
        "### 🔍 Change-Risk Intelligence",
        "",
        f"- **Calculated Risk Score**: `{report.change_risk.risk_score}`",
    ]

    if report.change_risk.high_risk_deletions:
        md.append("- ⚠️ **Stateful Deletions Detected**:")
        for res in report.change_risk.high_risk_deletions:
            md.append(f"  - `{res}` (forces replacement or deletion of stateful resource)")
    else:
        md.append("- ✅ **Stateful Deletions**: None detected")

    if report.change_risk.iam_broadening:
        md.append("- ⚠️ **IAM Policy Modifications**:")
        for res in report.change_risk.iam_broadening:
            md.append(f"  - `{res}`")
    else:
        md.append("- ✅ **IAM Broadening**: None detected")

    if report.security_failures:
        md.append("")
        md.append("### 🚨 Security Scanner Failures")
        for fail in report.security_failures[:5]:
            check_id = fail.get("check_id", "UNKNOWN")
            check_name = fail.get("check_name", "Check failed")
            md.append(f"- **{check_id}**: {check_name}")
        if len(report.security_failures) > 5:
            md.append(f"- _...and {len(report.security_failures) - 5} more issues._")

    md.extend([
        "",
        "> **Emulation Fidelity Disclosure**: Verification was executed against an isolated LocalStack sandbox container.",
        "> IAM policy enforcement and certain multi-region AWS constraints require live staging rehearsals.",
        "",
        "---",
        "_Generated automatically by ShadowPlane Verification Gateway._",
    ])

    return "\n".join(md)


def export_attestation_json(report: VerificationReport, output_file: str) -> str:
    """Exports the report as a signed/hashed JSON artifact."""
    report.compute_evidence_hash()
    data = report.to_dict()
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    return output_file
