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
# Resolve project root and import the core autonomous loop
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
import demo_loop  # noqa: E402


# ---------------------------------------------------------------------------
# CI-friendly output formatting
# ---------------------------------------------------------------------------
# GitHub Actions log grouping commands
# https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions
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
            "self-heals errors, and gates the CI/CD pipeline."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Exit codes:
  0   Verification PASSED — infrastructure is safe to deploy.
  1   Verification FAILED — blast radius could not be contained.

Examples:
  python cli.py --target-dir ./demo-infra
  python cli.py --target-dir ./infra --max-retries 3
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
        "--max-retries",
        type=int,
        default=5,
        help="Maximum self-healing retry attempts before failing (default: 5)",
    )
    return parser.parse_args()


async def run(args):
    """Execute the ShadowPlane verification pipeline."""
    target = os.path.abspath(args.target_dir)

    # ── Header ────────────────────────────────────────────────────────────
    banner("ShadowPlane Autonomous Verification Pipeline", char="=")
    print(f"  Target Directory : {target}")
    print(f"  Max Retries      : {args.max_retries}")
    print(f"  CI Environment   : {'GitHub Actions' if IS_GITHUB_ACTIONS else 'Standard'}")
    print(f"  Timestamp        : {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print()

    # Validate target directory exists
    if not os.path.isdir(target):
        msg = f"Target directory does not exist: {target}"
        ci_error(msg)
        print(f"[ERROR] {msg}", file=sys.stderr)
        return False

    # Check for main.tf
    main_tf = os.path.join(target, "main.tf")
    if not os.path.isfile(main_tf):
        msg = f"No main.tf found in target directory: {target}"
        ci_error(msg)
        print(f"[ERROR] {msg}", file=sys.stderr)
        return False

    # ── Execute the autonomous loop ──────────────────────────────────────
    ci_group_start("ShadowPlane: Autonomous Verification Loop")

    start_time = time.monotonic()
    success = await demo_loop.main(
        target_dir=target,
        max_retries=args.max_retries,
    )
    elapsed = time.monotonic() - start_time

    ci_group_end()

    # ── Result ───────────────────────────────────────────────────────────
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
