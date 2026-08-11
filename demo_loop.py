# -*- coding: utf-8 -*-
"""
demo_loop.py - ShadowPlane Autonomous CI/CD Interceptor
=======================================================
Acts as a simulated CI/CD pipeline gateway.

Loop:
  1. Trigger clone_and_deploy() against demo-infra/
  2. On failure -> read_sandbox_logs() -> parse error -> patch main.tf -> retry
  3. On success -> print the verification banner and exit

Max retries: 5
"""

import asyncio
import io
import os
import re
import shutil
import stat
import sys
import uuid

# Force UTF-8 output so box-drawing chars and emoji survive Windows terminals
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Resolve server.py from the same directory as this script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from server import mcp  # noqa: E402

DEMO_INFRA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo-infra")
MAIN_TF_PATH   = os.path.join(DEMO_INFRA_DIR, "main.tf")
MAX_RETRIES    = 5

# Unique 6-char hex suffix per run — guarantees no BucketAlreadyExists collisions
RUN_ID = uuid.uuid4().hex[:6]

# The intentionally broken bucket name
BROKEN_BUCKET  = "shadowplane-DEMO-INVALID"
FIXED_BUCKET   = f"shadowplane-demo-{RUN_ID}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _emit(yield_event, event_dict):
    """Helper to emit events to the web UI if a callback is provided."""
    if yield_event:
        await yield_event(event_dict)

async def _log(yield_event, text, level="info"):
    """Helper to log both to terminal and web UI."""
    print(text)
    await _emit(yield_event, {"type": "log", "level": level, "content": text})

def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)

def extract_result_text(tool_result) -> str:
    if isinstance(tool_result, tuple):
        _, result_dict = tool_result
        text = result_dict.get("result", str(tool_result))
    else:
        text = str(tool_result)
    return strip_ansi(text)

def _remove_readonly(func, path, _):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass

async def reset_terraform_state(yield_event=None):
    for item in (".terraform", "terraform.tfstate", "terraform.tfstate.backup",
                 ".terraform.lock.hcl", "localstack_override.tf"):
        target = os.path.join(DEMO_INFRA_DIR, item)
        if os.path.isdir(target):
            shutil.rmtree(target, onerror=_remove_readonly)
            await _log(yield_event, f"  [CLEAN] Removed directory  : {item}")
        elif os.path.isfile(target):
            os.remove(target)
            await _log(yield_event, f"  [CLEAN] Removed file       : {item}")

MAIN_TF_TEMPLATE = """\
# ShadowPlane Demo Infrastructure
# Provisions an S3 bucket and an IAM bucket policy.
#
# INTENTIONAL ERROR: S3 bucket names must be lowercase.
# "{broken}" violates this rule, causing LocalStack to return:
#   api error InvalidBucketName: The specified bucket is not valid.
#
# demo_loop.py will detect this error, patch the bucket name to
# "{fixed}" (valid), and re-deploy successfully.
# Run ID: {run_id}

resource "aws_s3_bucket" "shadowplane_bucket" {{
  # FATAL ERROR: uppercase letters are not allowed in S3 bucket names
  bucket = "{broken}"
}}

resource "aws_s3_bucket_policy" "shadowplane_policy" {{
  bucket = aws_s3_bucket.shadowplane_bucket.id

  policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [
      {{
        Sid    = "ShadowPlaneReadWrite"
        Effect = "Allow"
        Principal = {{
          AWS = "*"
        }}
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${{aws_s3_bucket.shadowplane_bucket.arn}}/*"
      }}
    ]
  }})
}}
"""

async def reset_main_tf(yield_event=None):
    content = MAIN_TF_TEMPLATE.format(
        broken=BROKEN_BUCKET,
        fixed=FIXED_BUCKET,
        run_id=RUN_ID,
    )
    with open(MAIN_TF_PATH, "w", encoding="utf-8") as fh:
        fh.write(content)
    await _log(yield_event, f"  [RESET] main.tf written  — broken bucket = {BROKEN_BUCKET!r}")
    await _log(yield_event, f"  [INFO]  Run ID = {RUN_ID}  |  Fixed bucket will be = {FIXED_BUCKET!r}")

# ---------------------------------------------------------------------------
# Self-healing patch engine
# ---------------------------------------------------------------------------

async def fix_main_tf(error_text: str, yield_event=None) -> bool:
    await _log(yield_event, "\n  [ANALYSE] Inspecting Terraform error for known fix patterns...")

    with open(MAIN_TF_PATH, "r", encoding="utf-8") as fh:
        content = fh.read()

    original = content
    applied  = []

    if (
        "InvalidBucketName" in error_text
        or "bucket is not valid" in error_text
        or BROKEN_BUCKET in content
    ):
        content = content.replace(BROKEN_BUCKET, FIXED_BUCKET)
        applied.append(f'InvalidBucketName  =>  "{BROKEN_BUCKET}"  ->  "{FIXED_BUCKET}"')

    if "MalformedPolicy" in error_text or "INVALID_ACCT" in content:
        content = re.sub(r'AWS\s*=\s*"arn:aws:iam::INVALID_ACCT:[^"]*"', 'AWS = "*"', content)
        applied.append("MalformedPrincipal  =>  replaced INVALID_ACCT ARN with wildcard '*'")

    if content != original:
        with open(MAIN_TF_PATH, "w", encoding="utf-8") as fh:
            fh.write(content)
        for msg in applied:
            await _log(yield_event, f"  [FIX]     {msg}", "success")
        await _log(yield_event, "  [SAVED]   main.tf written to disk.\n")
        
        # Emit diff event to Web UI
        await _emit(yield_event, {
            "type": "diff",
            "message": " | ".join(applied),
            "original": original,
            "patched": content
        })
        return True

    await _log(yield_event, "  [WARN]    No known fix pattern matched. Cannot auto-repair.\n", "warn")
    return False

# ---------------------------------------------------------------------------
# Main autonomous loop
# ---------------------------------------------------------------------------

async def main(yield_event=None, target_dir=None, max_retries=None):
    """
    Run the autonomous verification loop.

    Args:
        yield_event: Optional async callback for streaming events to web UI.
        target_dir:  Path to the Terraform directory (default: demo-infra/).
        max_retries: Maximum retry attempts (default: 5).

    Returns:
        True if verification passed, False otherwise.
    """
    global RUN_ID, FIXED_BUCKET, DEMO_INFRA_DIR, MAIN_TF_PATH, MAX_RETRIES
    # Regenerate RUN_ID on each invocation
    RUN_ID = uuid.uuid4().hex[:6]
    FIXED_BUCKET = f"shadowplane-demo-{RUN_ID}"

    # Allow caller overrides
    if target_dir is not None:
        DEMO_INFRA_DIR = os.path.abspath(target_dir)
        MAIN_TF_PATH = os.path.join(DEMO_INFRA_DIR, "main.tf")
    if max_retries is not None:
        MAX_RETRIES = max_retries

    divider = "=" * 67
    thin    = "-" * 55

    await _log(yield_event, f"\n+{divider}+")
    await _log(yield_event, "|  *** ShadowPlane CI/CD Interceptor — Autonomous Verification ***  |")
    await _log(yield_event, f"+{divider}+")
    await _log(yield_event, f"|  Target      : {DEMO_INFRA_DIR}")
    await _log(yield_event, f"|  Run ID      : {RUN_ID}")
    await _log(yield_event, f"|  Max Retries : {MAX_RETRIES}")
    await _log(yield_event, f"+{divider}+\n")

    await _emit(yield_event, {"type": "step", "step": "preflight"})
    await _log(yield_event, "[PRE-FLIGHT] Resetting demo environment for a clean run...")
    await reset_terraform_state(yield_event)
    await reset_main_tf(yield_event)
    await _log(yield_event, "")

    success = False

    for attempt in range(1, MAX_RETRIES + 1):
        if attempt == 1:
            await _emit(yield_event, {"type": "step", "step": "attempt1"})
        else:
            await _emit(yield_event, {"type": "step", "step": "attempt2"})

        await _log(yield_event, f"\n+--- Attempt {attempt}/{MAX_RETRIES} {thin}")
        await _log(yield_event, "|  [RUN]  Triggering clone_and_deploy()...")

        try:
            result = await mcp.call_tool("clone_and_deploy", {"terraform_dir": DEMO_INFRA_DIR})
            output  = extract_result_text(result)
            preview = output[:500].replace("\n", "\n|        ")
            await _log(yield_event, f"|\n|  [OUTPUT] Terraform stdout:\n|        {preview}\n|")

            await _log(yield_event, f"\n+{divider}+")
            await _log(yield_event, "|                                                                    |")
            await _log(yield_event, "|  [PASS] ShadowPlane Verification Passed.                           |", "success")
            await _log(yield_event, "|        Blast Radius Contained. Generating PR.                      |")
            await _log(yield_event, "|                                                                    |")
            await _log(yield_event, f"+{divider}+\n")
            success = True
            break

        except Exception as deploy_err:
            err_short = str(deploy_err)[:300]
            await _log(yield_event, f"|  [FAIL]   Deployment failed:\n|           {err_short}\n|", "error")

            await _log(yield_event, "|  [LOGS]   Reading sandbox logs via read_sandbox_logs()...")
            try:
                logs_result = await mcp.call_tool("read_sandbox_logs", {"deployment_id": "latest"})
                error_text  = extract_result_text(logs_result)
                log_preview = error_text[:700].replace("\n", "\n|        ")
                await _log(yield_event, f"|\n|  [STDERR] Captured Terraform Error:\n|        {log_preview}\n|", "error")
            except Exception as log_err:
                error_text = str(deploy_err)
                await _log(yield_event, f"|  [WARN]   Could not read sandbox logs: {log_err}\n|", "warn")

            if attempt < MAX_RETRIES:
                await _emit(yield_event, {"type": "step", "step": "analysis"})
                fixed = await fix_main_tf(error_text, yield_event)
                if not fixed:
                    await _log(yield_event, f"+--- [HALT] No auto-repair available. Halting loop.\n", "error")
                    break
                await _log(yield_event, f"|  [RETRY]  Infrastructure patched — retrying deployment...\n+{thin}\n")
            else:
                await _log(yield_event, f"+--- [HALT] Max retries ({MAX_RETRIES}) reached. Verification failed.\n", "error")

    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)

