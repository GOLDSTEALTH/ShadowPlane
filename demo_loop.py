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

from google import genai
from google.genai import types

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
# Self-healing patch engine (Gemini AI-powered)
# ---------------------------------------------------------------------------

GEMINI_MODEL = "gemini-3.7-flash"
GEMINI_FALLBACK_MODEL = "gemini-3.6-flash"

SYSTEM_INSTRUCTION = (
    "You are an expert AWS Terraform engineer. Fix the provided Terraform code "
    "to resolve the AWS API error. You must return ONLY the raw, valid HCL code. "
    "Do not include markdown formatting, backticks (```hcl), explanations, or "
    "apologies. Your exact output will be written directly to disk."
)


def _sanitize_hcl(raw: str) -> str:
    """
    Strip markdown code fences and language tags from LLM output.
    LLMs frequently wrap code in ```hcl ... ``` despite instructions not to.
    """
    text = raw.strip()
    # Remove leading ```hcl, ```terraform, or bare ```
    text = re.sub(r"^```(?:hcl|terraform|tf)?\s*\n?", "", text)
    # Remove trailing ```
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip() + "\n"


async def fix_main_tf(error_text: str, yield_event=None) -> bool:
    """
    Use Gemini AI to dynamically analyse and repair broken Terraform code.

    1. Reads the current main.tf content
    2. Sends it + the error logs to Gemini 3.7 Flash
    3. Writes the AI-patched HCL back to disk
    4. Emits diff events to the Web UI

    Returns True if the AI successfully produced a fix, False otherwise.
    """
    await _log(yield_event, "\n  [ANALYSE] Invoking Gemini AI to diagnose and repair Terraform error...")

    # Read current (broken) content
    with open(MAIN_TF_PATH, "r", encoding="utf-8") as fh:
        original = fh.read()

    # Build the user prompt
    user_prompt = (
        f"The following Terraform code failed during `terraform apply`.\n\n"
        f"## Terraform Error Output\n```\n{error_text}\n```\n\n"
        f"## Current main.tf\n```hcl\n{original}\n```\n\n"
        f"Fix the code so it provisions successfully against AWS (LocalStack). "
        f"Return ONLY the corrected HCL — nothing else."
    )

    try:
        # Initialize the Gemini client
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key or api_key == "your_gemini_api_key_here":
            await _log(yield_event, "  [WARN]    GEMINI_API_KEY not configured. Cannot invoke AI repair.", "warn")
            return False

        client = genai.Client(api_key=api_key)



        # Call Gemini with exponential backoff + model fallback
        MAX_API_RETRIES = 3
        BASE_DELAY = 2  # seconds
        response = None
        models_to_try = [GEMINI_MODEL, GEMINI_FALLBACK_MODEL]

        for model_name in models_to_try:
            await _log(yield_event, f"  [AI]      Model: {model_name}")
            await _log(yield_event, f"  [AI]      Sending {len(original)} bytes of HCL + error context...")

            model_succeeded = False
            for attempt in range(1, MAX_API_RETRIES + 1):
                try:
                    response = await asyncio.to_thread(
                        client.models.generate_content,
                        model=model_name,
                        contents=user_prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_INSTRUCTION,
                            temperature=0.1,
                        ),
                    )
                    model_succeeded = True
                    break  # Success — exit retry loop
                except Exception as api_err:
                    err_str = str(api_err)
                    is_retryable = any(code in err_str for code in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "overloaded"))
                    if is_retryable and attempt < MAX_API_RETRIES:
                        delay = BASE_DELAY ** attempt  # 2s, 4s, 8s
                        await _log(yield_event, f"  [RETRY]   {model_name} returned transient error (attempt {attempt}/{MAX_API_RETRIES}). Retrying in {delay}s...", "warn")
                        await asyncio.sleep(delay)
                    elif is_retryable and model_name != models_to_try[-1]:
                        await _log(yield_event, f"  [FALLBACK] {model_name} exhausted retries. Falling back to {GEMINI_FALLBACK_MODEL}...", "warn")
                        break  # Break inner loop, try next model
                    else:
                        raise  # Non-retryable or last model exhausted — propagate

            if model_succeeded:
                break

        if not response or not response.text:
            await _log(yield_event, "  [WARN]    Gemini returned an empty response. Cannot auto-repair.", "warn")
            return False

        # Sanitize the response (strip markdown fences)
        patched = _sanitize_hcl(response.text)

        await _log(yield_event, f"  [AI]      Received {len(patched)} bytes of patched HCL.")

        # Verify the AI actually changed something
        if patched.strip() == original.strip():
            await _log(yield_event, "  [WARN]    AI returned identical code. No fix applied.", "warn")
            return False

        # Write the patched code to disk
        with open(MAIN_TF_PATH, "w", encoding="utf-8") as fh:
            fh.write(patched)

        await _log(yield_event, "  [FIX]     Gemini AI patch applied successfully.", "success")
        await _log(yield_event, "  [SAVED]   main.tf written to disk.\n")

        # Emit diff event to Web UI
        await _emit(yield_event, {
            "type": "diff",
            "message": f"Gemini AI ({GEMINI_MODEL}) autonomous repair",
            "original": original,
            "patched": patched,
        })
        return True

    except Exception as e:
        await _log(yield_event, f"  [ERROR]   Gemini API call failed: {e}", "error")
        await _log(yield_event, "  [WARN]    Falling back — cannot auto-repair.\n", "warn")
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

