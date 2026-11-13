#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cli.py — ShadowPlane CLI Entrypoint
====================================
Production-grade, headless entrypoint for the ShadowPlane autonomous
infrastructure verification pipeline.

Designed for:
  - CI/CD runners (GitHub Actions, GitLab CI, Jenkins)
  - Docker containers (ENTRYPOINT ["python", "cli.py"])
  - Local developer workstations

Exit codes:
  0  — Verification passed (green gate)
  1  — Verification failed / blast radius uncontainable (red gate)
"""

import argparse
import asyncio
import os
import subprocess
import sys
import time

# ---------------------------------------------------------------------------
# Force UTF-8 stdout/stderr for consistent output across all platforms
# ---------------------------------------------------------------------------
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------------------
# Resolve project root and imports
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from engine.pipeline import VerificationPipeline  # noqa: E402
from engine.attestation import generate_markdown_attestation, export_attestation_json  # noqa: E402
from engine.security import CheckovValidator  # noqa: E402
from engine.runner import IaCRunner, LocalStackConnector  # noqa: E402
from engine.docker_runner import DockerIaCRunner  # noqa: E402
from engine.state_manager import StateSanitizer  # noqa: E402
from engine.notifications import SlackNotifier  # noqa: E402


# ---------------------------------------------------------------------------
# Version resolution
# ---------------------------------------------------------------------------
VERSION = os.environ.get("SHADOWPLANE_VERSION", "unknown")
version_file = os.path.join(PROJECT_ROOT, "VERSION")
if os.path.isfile(version_file):
    with open(version_file, "r", encoding="utf-8") as f:
        VERSION = f.read().strip()

# ---------------------------------------------------------------------------
# CI-friendly output formatting
# ---------------------------------------------------------------------------
IS_GITHUB_ACTIONS = os.environ.get("GITHUB_ACTIONS") == "true"


def ci_group_start(title: str):
    """Open a collapsible log group in GitHub Actions."""
    if IS_GITHUB_ACTIONS:
        print(f"::group::{title}")


def ci_group_end():
    """Close a collapsible log group in GitHub Actions."""
    if IS_GITHUB_ACTIONS:
        print("::endgroup::")


def ci_error(message: str):
    """Emit a GitHub Actions error annotation."""
    if IS_GITHUB_ACTIONS:
        print(f"::error::{message}")


def ci_notice(message: str):
    """Emit a GitHub Actions notice annotation."""
    if IS_GITHUB_ACTIONS:
        print(f"::notice::{message}")


def banner(text: str, char: str = "=", width: int = 72):
    """Print a visually prominent banner for CI terminals."""
    border = char * width
    print(f"\n{border}")
    print(f"  {text}")
    print(f"{border}\n")


# ---------------------------------------------------------------------------
# Main CLI logic
# ---------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(
        prog="shadowplane",
        description=(
            "ShadowPlane — Autonomous Infrastructure Verification Pipeline. "
            "Intercepts Terraform deployments, runs them in a LocalStack sandbox, "
            "evaluates change-risk intelligence, and gates the CI/CD pipeline."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Exit codes:
  0   Verification PASSED — infrastructure is safe to deploy.
  1   Verification FAILED — blast radius could not be contained or critical risk detected.

Examples:
  python cli.py --target-dir ./demo-infra
  python cli.py --target-dir ./infra --output-json attestation.json
  python cli.py --target-dir ./infra --no-docker --pr 42
  python cli.py --target-dir ./demo-infra --demo
  docker run shadowplane --target-dir /workspace/infra
""",
    )
    parser.add_argument(
        "--target-dir",
        type=str,
        default=os.path.join(PROJECT_ROOT, "demo-infra"),
        help="Path to the Terraform directory to verify (default: ./demo-infra)",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default=None,
        help="Path to export the signed JSON attestation pack",
    )
    parser.add_argument(
        "--no-docker",
        action="store_true",
        default=False,
        help="Force host-level execution instead of Docker container runner",
    )
    parser.add_argument(
        "--pr",
        type=str,
        default=None,
        help="Optional PR number for Slack notifications",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        default=False,
        help="Run legacy interactive self-healing demo loop",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=5,
        help="Maximum self-healing retry attempts before failing (demo mode only, default: 5)",
    )
    parser.add_argument(
        "--ai-model",
        type=str,
        default="gemini/gemini-3.7-flash",
        help="The AI model to use for self-healing (demo mode only, default: gemini/gemini-3.7-flash)",
    )
    parser.add_argument(
        "--ai-base-url",
        type=str,
        default=None,
        help="Optional custom base URL for the AI provider (demo mode only)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"ShadowPlane Gatekeeper v{VERSION}",
        help="Show the version and exit",
    )
    return parser.parse_args()


async def run(args):
    """Execute the ShadowPlane verification pipeline."""
    target = os.path.abspath(args.target_dir)

    # ── Header ────────────────────────────────────────────────────────────
    banner("ShadowPlane Autonomous Verification Pipeline", char="=")
    print(f"  Version          : v{VERSION}")
    print(f"  Target Directory : {target}")
    print(f"  Execution Mode   : {'Interactive Demo' if args.demo else 'Verification Gateway'}")
    print(f"  Container Sandbox: {'Disabled (--no-docker)' if args.no_docker else 'Enabled'}")
    print(f"  CI Environment   : {'GitHub Actions' if IS_GITHUB_ACTIONS else 'Standard'}")
    print(f"  Timestamp        : {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print()

    # Validate target directory exists
    if not os.path.isdir(target):
        msg = f"Target directory does not exist: {target}"
        ci_error(msg)
        print(f"[ERROR] {msg}", file=sys.stderr)
        return False

    # Validate target contains at least one .tf file
    tf_files = [f for f in os.listdir(target) if f.endswith(".tf")]
    if not tf_files:
        msg = f"No .tf files found in target directory: {target}"
        ci_error(msg)
        print(f"[ERROR] {msg}", file=sys.stderr)
        return False

    # ── Legacy Demo Mode ──────────────────────────────────────────────────
    if args.demo:
        import demo_loop
        ci_group_start("ShadowPlane: Autonomous Demo Loop")
        start_time = time.monotonic()
        success = await demo_loop.main(
            target_dir=target,
            max_retries=args.max_retries,
            ai_model=args.ai_model,
            ai_base_url=args.ai_base_url,
        )
        elapsed = time.monotonic() - start_time
        ci_group_end()

        print()
        if success:
            banner("RESULT: VERIFICATION PASSED", char="=")
            print("  Infrastructure is safe to deploy.")
            print(f"  Elapsed: {elapsed:.1f}s")
            ci_notice(f"ShadowPlane verification passed in {elapsed:.1f}s")
        else:
            banner("RESULT: VERIFICATION FAILED", char="!")
            print("  Blast radius could NOT be contained.")
            print("  The deployment pipeline should be BLOCKED.")
            print(f"  Elapsed: {elapsed:.1f}s")
            ci_error(f"ShadowPlane verification failed after {elapsed:.1f}s")

        return success

    # ── Standard Verification Gateway Mode ────────────────────────────────
    ci_group_start("ShadowPlane: Verification Pipeline Gateway")
    start_time = time.monotonic()

    # Configure runner
    if args.no_docker:
        runner = IaCRunner(
            binary=os.environ.get("SHADOWPLANE_IAC_BINARY", "terraform"),
            connector=LocalStackConnector(),
        )
    else:
        docker_runner = DockerIaCRunner(connector=LocalStackConnector())
        if docker_runner.is_available:
            runner = docker_runner
        else:
            print("[WARN] Docker is not available. Falling back to host-level IaCRunner.", file=sys.stderr)
            runner = IaCRunner(
                binary=os.environ.get("SHADOWPLANE_IAC_BINARY", "terraform"),
                connector=LocalStackConnector(),
            )

    # Ingest and sanitize state
    sanitizer = StateSanitizer(target)
    sanitizer.ingest_and_sanitize()
    try:
        # Extract commit SHA if in git repo
        commit_sha = None
        try:
            proc = subprocess.run(
                ["git", "rev-parse", "--short=12", "HEAD"],
                cwd=target,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                commit_sha = proc.stdout.strip()
        except Exception:
            pass

        pipeline = VerificationPipeline(
            terraform_dir=target,
            runner=runner,
            security=CheckovValidator(),
            commit_sha=commit_sha,
        )
        report = pipeline.run()
    finally:
        sanitizer.restore_backup()

    elapsed = time.monotonic() - start_time
    ci_group_end()

    # Generate Markdown attestation card
    attestation_md = generate_markdown_attestation(report)
    print()
    print(attestation_md)
    print()

    # Export JSON attestation pack if requested
    if args.output_json:
        export_attestation_json(report, args.output_json)
        print(f"[INFO] Exported attestation JSON to: {args.output_json}")

    # Append to GITHUB_STEP_SUMMARY if configured
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        try:
            with open(step_summary, "a", encoding="utf-8") as f:
                f.write(attestation_md + "\n\n")
        except Exception as e:
            print(f"[WARN] Failed to write to GITHUB_STEP_SUMMARY: {e}", file=sys.stderr)

    # Send Slack notification if webhook URL is configured
    if os.environ.get("SLACK_WEBHOOK_URL"):
        notifier = SlackNotifier()
        notifier.send_attestation_report(args.pr or "N/A", attestation_md, report.success)

    # Result banner & annotations
    if report.success:
        banner("RESULT: VERIFICATION PASSED", char="=")
        print("  Infrastructure is safe to deploy.")
        print(f"  Elapsed: {elapsed:.1f}s")
        ci_notice(f"ShadowPlane verification passed in {elapsed:.1f}s")
    else:
        banner("RESULT: VERIFICATION FAILED", char="!")
        print("  Verification failed or critical change-risk detected.")
        print("  The deployment pipeline should be BLOCKED.")
        print(f"  Elapsed: {elapsed:.1f}s")
        ci_error(f"ShadowPlane verification failed after {elapsed:.1f}s")

    return report.success


def main():
    args = parse_args()

    try:
        success = asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Pipeline aborted by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as exc:
        ci_error(f"ShadowPlane crashed: {exc}")
        print(f"\n[FATAL] Unhandled exception: {exc}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
