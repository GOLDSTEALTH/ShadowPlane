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
import os
import re
import shutil
import stat
import sys
import tempfile
import uuid

# Force UTF-8 output so box-drawing chars and emoji survive Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Resolve server.py from the same directory as this script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from server import mcp  # noqa: E402
from circuit_breaker import CircuitBreakerError  # noqa: E402
from engine.ai import repair_terraform_code  # noqa: E402

DEFAULT_DEMO_INFRA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo-infra")
DEMO_INFRA_DIR = DEFAULT_DEMO_INFRA_DIR
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

async def reset_terraform_state(infra_dir: str, yield_event=None):
    for item in (".terraform", "terraform.tfstate", "terraform.tfstate.backup",
                 ".terraform.lock.hcl", "localstack_override.tf"):
        target = os.path.join(infra_dir, item)
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

async def reset_main_tf(infra_dir: str, yield_event=None):
    content = MAIN_TF_TEMPLATE.format(
        broken=BROKEN_BUCKET,
        fixed=FIXED_BUCKET,
        run_id=RUN_ID,
    )
    main_tf_path = os.path.join(infra_dir, "main.tf")
    with open(main_tf_path, "w", encoding="utf-8") as fh:
        fh.write(content)
    await _log(yield_event, f"  [RESET] main.tf written  — broken bucket = {BROKEN_BUCKET!r}")
    await _log(yield_event, f"  [INFO]  Run ID = {RUN_ID}  |  Fixed bucket will be = {FIXED_BUCKET!r}")

async def fix_main_tf(infra_dir: str, error_text: str, ai_model: str, ai_base_url: str = None, yield_event=None) -> bool:
    """
    Use the unified AI Engine (LiteLLM) to dynamically analyse and repair broken Terraform code.
    """
    await _log(yield_event, f"\n  [ANALYSE] Invoking AI ({ai_model}) to diagnose and repair Terraform error...")

    main_tf_path = os.path.join(infra_dir, "main.tf")
    if not os.path.isfile(main_tf_path):
        await _log(yield_event, f"  [WARN]    No main.tf found in {infra_dir}", "warn")
        return False

    # Read current (broken) content
    with open(main_tf_path, "r", encoding="utf-8") as fh:
        original = fh.read()

    patched = await repair_terraform_code(
        model=ai_model,
        base_url=ai_base_url,
        error_text=error_text,
        current_hcl=original
    )

    if not patched:
        await _log(yield_event, "  [WARN]    AI repair failed or returned empty response.", "warn")
        return False

    if patched.strip() == original.strip():
        await _log(yield_event, "  [WARN]    AI returned identical code. No fix applied.", "warn")
        return False

    # Write the patched code to disk
    with open(main_tf_path, "w", encoding="utf-8") as fh:
        fh.write(patched)

    await _log(yield_event, "  [FIX]     AI patch applied successfully.", "success")
    await _log(yield_event, "  [SAVED]   main.tf written to disk.\n")

    # Emit diff event to Web UI
    await _emit(yield_event, {
        "type": "diff",
        "message": f"AI ({ai_model}) autonomous repair",
        "original": original,
        "patched": patched,
    })
    return True


# ---------------------------------------------------------------------------
# Main autonomous loop
# ---------------------------------------------------------------------------

async def main(yield_event=None, target_dir=None, max_retries=None, ai_model="gemini/gemini-3.7-flash", ai_base_url=None, github_repo=None, base_branch="main", pr_branch=None):
    """
    Run the autonomous verification loop.

    Args:
        yield_event: Optional async callback for streaming events to web UI.
        target_dir:  Path to the Terraform directory (default: demo-infra/).
        max_retries: Maximum retry attempts (default: 5).

    Returns:
        True if verification passed, False otherwise.
    """
    global RUN_ID, FIXED_BUCKET
    # Regenerate RUN_ID on each invocation
    RUN_ID = uuid.uuid4().hex[:6]
    FIXED_BUCKET = f"shadowplane-demo-{RUN_ID}"

    max_attempts = max_retries if max_retries is not None else MAX_RETRIES

    workspace_dir = None
    try:
        if github_repo and pr_branch:
            from engine.git_utils import clone_and_checkout, checkout_branch
            await _log(yield_event, f"\n[STEP 0] PRE-WARM SANDBOX")
            await _log(yield_event, f"  -> Cloning {github_repo} into sandbox...")
            repo_url = f"https://github.com/{github_repo}.git"
            workspace_dir = os.path.join(tempfile.gettempdir(), f"shadowplane-{RUN_ID}")
            
            success = clone_and_checkout(repo_url, base_branch, pr_branch, workspace_dir)
            if not success:
                raise Exception("Git Clone Failed")
                
            infra_dir = workspace_dir
            
            await _log(yield_event, f"  -> Pre-Warming Base Branch ({base_branch})...")
            try:
                await mcp.call_tool("clone_and_deploy", {"terraform_dir": infra_dir})
                await _log(yield_event, "  -> Pre-Warm Successful. Mock production state created.", "success")
            except Exception as e:
                await _log(yield_event, f"  [WARN] Pre-warm apply failed: {str(e)[:200]}. Proceeding with clean state...", "warn")
                
            await _log(yield_event, f"\n[STEP 1] TRANSITION TO PR BRANCH ({pr_branch})")
            checkout_success = checkout_branch(workspace_dir, pr_branch)
            if not checkout_success:
                await _log(yield_event, f"  [ERROR] Failed to checkout PR branch '{pr_branch}'. Aborting.", "error")
                return False
        else:
            infra_dir = os.path.abspath(target_dir) if target_dir is not None else DEFAULT_DEMO_INFRA_DIR
            is_demo_mode = os.path.normcase(os.path.abspath(infra_dir)) == os.path.normcase(os.path.abspath(DEFAULT_DEMO_INFRA_DIR))
            
            if is_demo_mode:
                await _log(yield_event, "[PRE-FLIGHT] Resetting demo environment for a clean run...")
                await reset_terraform_state(infra_dir, yield_event)
                await reset_main_tf(infra_dir, yield_event)
            else:
                await _log(yield_event, "[PRE-FLIGHT] Verifying user-supplied infrastructure directory...")
                if not os.path.isdir(infra_dir):
                    await _log(yield_event, f"  [ERROR] Target directory does not exist: {infra_dir}", "error")
                    return False
                tf_files = [f for f in os.listdir(infra_dir) if f.endswith('.tf')]
                if not tf_files:
                    await _log(yield_event, f"  [ERROR] No .tf files found in: {infra_dir}", "error")
                    return False
                await _log(yield_event, f"  [OK] Found {len(tf_files)} Terraform file(s). Proceeding without reset.")

        divider = "=" * 67
        thin    = "-" * 55

        await _log(yield_event, f"\n+{divider}+")
        await _log(yield_event, "|  *** ShadowPlane CI/CD Interceptor — Autonomous Verification ***  |")
        await _log(yield_event, f"+{divider}+")
        await _log(yield_event, f"|  Target      : {infra_dir}")
        await _log(yield_event, f"|  Run ID      : {RUN_ID}")
        await _log(yield_event, f"|  Max Retries : {max_attempts}")
        await _log(yield_event, f"+{divider}+\n")

        await _emit(yield_event, {"type": "step", "step": "preflight"})
        await _log(yield_event, "")

        success = False

        for attempt in range(1, max_attempts + 1):
            if attempt == 1:
                await _emit(yield_event, {"type": "step", "step": "attempt1"})
            else:
                await _emit(yield_event, {"type": "step", "step": "attempt2"})

            await _log(yield_event, f"\n+--- Attempt {attempt}/{max_attempts} {thin}")
            await _log(yield_event, "|  [RUN]  Triggering clone_and_deploy()...")

            try:
                result = await mcp.call_tool("clone_and_deploy", {"terraform_dir": infra_dir})
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

            except CircuitBreakerError as cb_err:
                await _log(yield_event, f"|  [BLOCKED] Circuit breaker tripped — execution halted.", "error")
                await _log(yield_event, f"|  {str(cb_err)[:300]}\n|", "error")
                await _log(yield_event, f"+--- [HALT] Circuit breaker active. Human intervention required.\n", "error")
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

                if attempt < max_attempts:
                    await _emit(yield_event, {"type": "step", "step": "analysis"})
                    fixed = await fix_main_tf(infra_dir, error_text, ai_model, ai_base_url, yield_event)
                    if not fixed:
                        await _log(yield_event, f"+--- [HALT] No auto-repair available. Halting loop.\n", "error")
                        break
                    await _log(yield_event, f"|  [RETRY]  Infrastructure patched — retrying deployment...\n+{thin}\n")
                else:
                    await _log(yield_event, f"+--- [HALT] Max retries ({max_attempts}) reached. Verification failed.\n", "error")

        return success
    finally:
        if workspace_dir and os.path.exists(workspace_dir):
            shutil.rmtree(workspace_dir, onerror=_remove_readonly)

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
