# ShadowPlane — LLM-Executable Engineering Workplan

> **Purpose**: This document is a self-contained work breakdown that any capable coding LLM can pick up and execute. Each work package includes exact file paths, current code state, target code patterns, and acceptance criteria.
>
> **Codebase**: `e:\ShadowPlane` (or wherever the repo is cloned)
> **Language**: Python 3.10+, TypeScript/React (landing page)
> **Phase 0 Status**: ✅ Complete (destructive behavior fixed, false greens eliminated, security scanning hardened)

---

## Architecture Context (Read First)

The codebase currently has **two disconnected pipelines**:

```
Pipeline A ("CLI/MCP"):
  cli.py → demo_loop.py → server.py (FastMCP)
  Uses: Terraform, LiteLLM, LocalStack
  Entry points: `shadowplane`, `shadowplane-server`
  
Pipeline B ("Enterprise Engine"):
  main.py → engine/* (runner, security, state_manager, ai, notifications, git_utils)
  Uses: OpenTofu (configurable), Google GenAI, Checkov, Slack
  Entry point: `shadowplane-engine`
```

**The goal of this work is to merge these into a single unified pipeline.**

### Key Files Reference

| File | Purpose | Lines |
|------|---------|-------|
| `cli.py` | CLI entrypoint, parses args, calls `demo_loop.main()` | 222 |
| `demo_loop.py` | Autonomous deploy-diagnose-repair loop | 334 |
| `server.py` | FastMCP server with `clone_and_deploy`, `read_sandbox_logs`, `reset_circuit_breaker` | 524 |
| `web_server.py` | FastAPI webhook gateway, WebSocket streaming | 343 |
| `circuit_breaker.py` | Per-directory failure tracking with sliding window | 217 |
| `main.py` | Enterprise engine orchestrator | 167 |
| `engine/ai.py` | LiteLLM AI repair wrapper | 133 |
| `engine/runner.py` | IaC runner with `EmulatorConnector` abstraction | 148 |
| `engine/security.py` | Checkov scanner wrapper | 58 |
| `engine/state_manager.py` | Terraform state sanitizer | ~75 |
| `engine/git_utils.py` | Git clone/checkout helpers | 65 |
| `engine/notifications.py` | Slack webhook notifier | 86 |
| `engine/logger.py` | Simple logging setup | ~15 |
| `pyproject.toml` | Build config, 3 entry points | 48 |
| `requirements.txt` | Pip dependencies | ~15 |

---

## Work Package 1: CLI Argument Pass-Through Fix

**Priority**: Quick win (30 min)
**Dependencies**: None
**Assignable independently**: ✅ Yes

### Problem

`cli.py` accepts `--ai-model` and `--ai-base-url` arguments but **drops them** when calling `demo_loop.main()`. See `cli.py` lines 179-182:

```python
success = await demo_loop.main(
    target_dir=target,
    max_retries=args.max_retries,
)
```

The `ai_model` and `ai_base_url` parameters are accepted by `demo_loop.main()` (see its signature at line 189) but never passed.

### Instructions

1. Open `cli.py`
2. Find the call to `demo_loop.main()` at line 179-182
3. Change it to:
```python
success = await demo_loop.main(
    target_dir=target,
    max_retries=args.max_retries,
    ai_model=args.ai_model,
    ai_base_url=args.ai_base_url,
)
```

### Acceptance Criteria
- `cli.py` passes `py_compile`
- Running `shadowplane --ai-model gpt-4o --target-dir ./demo-infra` passes the model through to `demo_loop.main()`
- Existing tests still pass

---

## Work Package 2: Landing Page Claims Cleanup

**Priority**: High (reputational risk)
**Dependencies**: None
**Assignable independently**: ✅ Yes

### Problem

The landing page contains claims with no supporting code. These need to be replaced with honest descriptions of actual capabilities.

### File: `landing-page/src/components/EngineeringSpecs.tsx`

Replace the `specs` array (lines 2-38) with:

```typescript
const specs = [
    {
      icon: "🧠",
      header: "Bring-Your-Own-Model",
      body: "Native LiteLLM integration supports GPT-4o, Claude 3.5, Gemini 3.7, and Ollama for AI-assisted Terraform repair.",
      tag: "BYOM",
    },
    {
      icon: "🧊",
      header: "Two-Stage Pre-Warm Sandbox",
      body: "Safely simulates production state updates. Clones 'main' to build a mock environment, then applies your PR branch on top.",
      tag: "SAFE-STATE",
    },
    {
      icon: "🛡",
      header: "LocalStack Sandbox Isolation",
      body: "Terraform execution is redirected to a LocalStack container with mock credentials. Network egress controls are roadmapped.",
      tag: "SECURITY",
    },
    {
      icon: "🔒",
      header: "Circuit Breaker Safety",
      body: "Prevents runaway agent retry loops. After 4 consecutive failures, execution is hard-blocked until a human operator intervenes.",
      tag: "SAFETY",
    },
    {
      icon: "⚡",
      header: "CI/CD Integration",
      body: "Drop-in GitHub Actions support. Headless CLI with deterministic exit codes (0 = pass, 1 = fail) for any CI runner.",
      tag: "CI-CD",
    },
    {
      icon: "🔍",
      header: "Security Scanning",
      body: "Integrated Checkov static analysis with fail-closed enforcement. Missing scanner binary blocks the pipeline, not bypasses it.",
      tag: "SCANNING",
    },
  ];
```

### File: `landing-page/src/components/BusinessROI.tsx`

Replace the `stats` array (lines 2-24) with:

```typescript
const stats = [
    {
      id: "feedback",
      value: "Minutes",
      subtitle: "Infrastructure Feedback Loop",
      detail:
        "Catch deployment failures in a sandbox before they reach production. No cloud credentials required.",
    },
    {
      id: "blast",
      value: "Sandboxed",
      subtitle: "Blast Radius Containment",
      detail:
        "Invalid cloud configurations are tested against LocalStack before any production deployment is attempted.",
    },
    {
      id: "footprint",
      value: "Zero",
      subtitle: "Production Agent Footprint",
      detail:
        "Operates entirely via webhooks and localized Docker/LocalStack sandboxes.",
    },
  ];
```

### Claims Removed and Why

| Old Claim | Why Removed |
|-----------|-------------|
| "AST failsafe parser" | Implementation is regex-based (`re.search` for backticks). No AST parsing exists. |
| "Firecracker microVMs" | Zero Firecracker code in the repository. |
| "Sub-100ms cold starts via Warm Pools" | No warm pool implementation exists. Single static container. |
| "100% Blast Radius Containment" | Host-level `subprocess.run` execution. `local-exec` can escape. |
| "45m → 12s MTTR" | No benchmark evidence. Only measures LLM API latency. |
| "Mandatory human review gates" | `reset_circuit_breaker` is an unauthenticated MCP tool. |
| "Agent rigidly scoped to .tf files" | `read_sandbox_logs` returns full stderr. |

### Acceptance Criteria
- No claims reference capabilities that don't exist in the codebase
- Landing page still builds: `cd landing-page && npm run build`
- All replaced text is factually accurate based on current source code

---

## Work Package 3: Unified Verification Pipeline

**Priority**: Critical (core architecture)
**Dependencies**: Work Package 1
**Assignable independently**: ✅ Yes (largest package — can be split further)
**Estimated effort**: 2-3 days

### Goal

Create a single `engine/pipeline.py` module that both Pipeline A and Pipeline B call. This replaces the ad-hoc logic in `demo_loop.py` and `main.py` with one contract.

### Step 3.1: Create `engine/pipeline.py` (NEW FILE)

Create `engine/pipeline.py` with this structure:

```python
"""
engine/pipeline.py — Unified ShadowPlane Verification Pipeline
===============================================================
Single source of truth for the verification contract.
All entry points (CLI, MCP, webhook, enterprise engine) call this.
"""

import os
import time
import hashlib
import json
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional

logger = logging.getLogger("ShadowPlane-Pipeline")


class VerificationStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"  # circuit breaker


@dataclass
class VerificationReport:
    """The output contract. Every verification run produces exactly one of these."""
    timestamp: str = ""
    terraform_dir: str = ""
    commit_sha: Optional[str] = None

    # Individual stage results
    init_result: VerificationStatus = VerificationStatus.SKIP
    security_result: VerificationStatus = VerificationStatus.SKIP
    deploy_result: VerificationStatus = VerificationStatus.SKIP
    repair_applied: bool = False
    repair_approved: bool = False

    # Detail fields
    init_error: str = ""
    security_failures: list = field(default_factory=list)
    deploy_error: str = ""
    deploy_stdout: str = ""

    # Coverage
    verified_services: list = field(default_factory=list)
    unsupported_services: list = field(default_factory=list)

    # Evidence
    evidence_hash: str = ""

    @property
    def success(self) -> bool:
        """Overall pass requires ALL mandatory stages to pass."""
        return (
            self.init_result == VerificationStatus.PASS
            and self.security_result == VerificationStatus.PASS
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
    Orchestrates: init -> security scan -> deploy -> (optional repair loop) -> final report.
    
    Usage:
        pipeline = VerificationPipeline(
            terraform_dir="./infra",
            runner=IaCRunner(...),
            security=CheckovValidator(),
            ai_repairer=None,  # or a callable for repair
            max_repair_attempts=3,
        )
        report = pipeline.run()
    """

    def __init__(
        self,
        terraform_dir: str,
        runner,          # engine.runner.IaCRunner instance
        security,        # engine.security.CheckovValidator instance  
        ai_repairer=None,  # async callable(error_text, current_hcl) -> patched_hcl | None
        max_repair_attempts: int = 3,
        commit_sha: str = None,
    ):
        self.terraform_dir = os.path.abspath(terraform_dir)
        self.runner = runner
        self.security = security
        self.ai_repairer = ai_repairer
        self.max_repair_attempts = max_repair_attempts
        self.commit_sha = commit_sha

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

        # Stage 2: Security Scan (MANDATORY — runs BEFORE apply)
        logger.info("[2/4] Security Scan (pre-apply)")
        sec_result = self.security.scan(self.terraform_dir)
        if not sec_result["passed"]:
            report.security_result = VerificationStatus.FAIL
            report.security_failures = sec_result.get("failed_checks", [])
            # Don't return yet — still attempt apply for full diagnostics
            # But the overall report.success will be False
        else:
            report.security_result = VerificationStatus.PASS

        # Stage 3: Deploy to sandbox
        logger.info("[3/4] Sandbox Deploy")
        apply_res = self.runner.apply(self.terraform_dir)
        report.deploy_stdout = apply_res.get("stdout", "")

        if apply_res["success"]:
            report.deploy_result = VerificationStatus.PASS
        else:
            report.deploy_result = VerificationStatus.FAIL
            report.deploy_error = apply_res.get("stderr", "")

            # Stage 3b: Optional AI repair loop
            if self.ai_repairer and self.max_repair_attempts > 0:
                logger.info("[3b/4] AI Repair Loop (opt-in)")
                # NOTE: Repair is proposed, not auto-applied in production.
                # This section is for interactive/demo use only.
                report.repair_applied = False  # Set to True only if repair succeeds

        # Stage 4: Post-deploy security scan (catch issues introduced by repair)
        if report.deploy_result == VerificationStatus.PASS and report.security_result != VerificationStatus.PASS:
            logger.info("[4/4] Post-deploy security re-scan")
            sec_result2 = self.security.scan(self.terraform_dir)
            if sec_result2["passed"]:
                report.security_result = VerificationStatus.PASS
                report.security_failures = []
            else:
                report.security_failures = sec_result2.get("failed_checks", [])

        report.compute_evidence_hash()
        return report
```

### Step 3.2: Rewire `main.py` to use `VerificationPipeline`

Replace the `run_pipeline` method body in `main.py` to instantiate and call `VerificationPipeline`. The key change: instead of the current ad-hoc orchestration with inline Checkov calls and asyncio.run conflicts, it becomes:

```python
from engine.pipeline import VerificationPipeline, VerificationReport

def run_pipeline(self) -> bool:
    pipeline = VerificationPipeline(
        terraform_dir=self.target_dir,
        runner=self.runner,
        security=self.security,
        commit_sha=None,  # TODO: extract from git
        max_repair_attempts=3,
    )
    report = pipeline.run()
    
    # Log the report
    self.log.info(f"Verification Report: {report.to_dict()}")
    
    # Notify
    if report.success:
        self.notifier.send_verification_success(
            self.pr_number, "", ""  # TODO: pass actual HCL diffs
        )
    
    return report.success
```

### Step 3.3: Rewire `demo_loop.py` to use `VerificationPipeline` (or keep as demo wrapper)

`demo_loop.py` is the interactive demo/CLI path. It can continue to exist as a wrapper that:
1. Sets up the demo environment (if in demo mode)
2. Calls `VerificationPipeline.run()`
3. If repair is enabled, runs the AI repair loop using `engine/ai.py`
4. Streams events to the web UI via `yield_event`

The key constraint: `demo_loop.py` must NOT bypass the pipeline's security scan. Currently it does zero security scanning.

### Step 3.4: Update `pyproject.toml` entry points

Consider reducing to 2 entry points:
```toml
[project.scripts]
shadowplane        = "cli:main"
shadowplane-server = "server:_cli_entry"
```

The `shadowplane-engine` entry point should become redundant once `main.py` uses the same pipeline as `cli.py`.

### Acceptance Criteria
- `engine/pipeline.py` exists with `VerificationPipeline` and `VerificationReport`
- `main.py` calls `VerificationPipeline.run()` instead of inline orchestration
- Security scanning runs on EVERY verification (never skipped)
- All existing tests pass
- New test file `test_pipeline.py` with at least:
  - Test that init failure → report.success is False
  - Test that security failure → report.success is False even if deploy passes
  - Test that deploy failure → report.success is False
  - Test that all-pass → report.success is True
  - Test that evidence_hash is populated

---

## Work Package 4: MCP Auth Gate for Circuit Breaker Reset

**Priority**: Medium
**Dependencies**: None
**Assignable independently**: ✅ Yes

### Problem

`reset_circuit_breaker` in `server.py` (line 502) is exposed as an unauthenticated MCP tool. Any AI agent can call it to self-reset its own breaker, defeating the "human-only" safety gate.

### Instructions

1. Open `server.py`
2. Find the `reset_circuit_breaker` MCP tool (line 502-515)
3. Add an environment-variable-based auth gate:

```python
@mcp.tool()
async def reset_circuit_breaker(terraform_dir: str, auth_token: str = "") -> str:
    """Reset the circuit breaker for a Terraform directory after human intervention.

    Use this tool after diagnosing and fixing the root cause of repeated Terraform
    failures. This unblocks clone_and_deploy for the specified directory.

    Args:
        terraform_dir: Path to the Terraform directory whose circuit breaker should be reset.
        auth_token: Required authentication token. Must match SHADOWPLANE_RESET_TOKEN env var.
    """
    expected_token = os.environ.get("SHADOWPLANE_RESET_TOKEN", "")
    if not expected_token:
        logger.warning("SHADOWPLANE_RESET_TOKEN not configured — circuit breaker reset is disabled.")
        return (
            "Circuit breaker reset is disabled. "
            "Set the SHADOWPLANE_RESET_TOKEN environment variable to enable manual resets."
        )
    
    if not auth_token or auth_token != expected_token:
        logger.warning("Invalid auth_token provided for reset_circuit_breaker on '%s'", terraform_dir)
        return (
            "Authentication failed. Provide a valid auth_token to reset the circuit breaker. "
            "This token must match the SHADOWPLANE_RESET_TOKEN environment variable."
        )
    
    logger.info("reset_circuit_breaker tool invoked for: %s (authenticated)", terraform_dir)
    result = circuit_breaker.reset(terraform_dir)
    logger.info("reset_circuit_breaker result: %s", result)
    return result
```

4. Add `SHADOWPLANE_RESET_TOKEN` to `.env.example`:
```
SHADOWPLANE_RESET_TOKEN=your_reset_token_here
```

### Acceptance Criteria
- `reset_circuit_breaker` requires `auth_token` parameter
- Without `SHADOWPLANE_RESET_TOKEN` env var, all resets are denied
- With correct token, reset works as before
- With wrong token, reset is denied with clear error message
- Existing circuit breaker tests still pass
- `server.py` passes `py_compile`

---

## Work Package 5: Git Checkout Error Handling

**Priority**: Medium
**Dependencies**: None
**Assignable independently**: ✅ Yes

### Problem

In `demo_loop.py` line 249-250, the return value of `checkout_branch()` is ignored. If the PR branch checkout fails, the loop verifies the base branch while reporting on the PR branch.

### Instructions

1. Open `demo_loop.py`
2. Find line 249-250:
```python
        await _log(yield_event, f"\n[STEP 1] TRANSITION TO PR BRANCH ({pr_branch})")
        checkout_branch(workspace_dir, pr_branch)
```
3. Replace with:
```python
        await _log(yield_event, f"\n[STEP 1] TRANSITION TO PR BRANCH ({pr_branch})")
        checkout_success = checkout_branch(workspace_dir, pr_branch)
        if not checkout_success:
            await _log(yield_event, f"  [ERROR] Failed to checkout PR branch '{pr_branch}'. Aborting.", "error")
            return False
```

4. Similarly, fix the pre-warm failure handling at lines 242-246. Currently:
```python
        try:
            await mcp.call_tool("clone_and_deploy", {"terraform_dir": DEMO_INFRA_DIR})
            await _log(yield_event, "  -> Pre-Warm Successful. Mock production state created.", "success")
        except Exception as e:
            await _log(yield_event, "  [WARN] Pre-warm apply failed. Proceeding anyway...", "warn")
```
This should log the actual error for debugging:
```python
        try:
            await mcp.call_tool("clone_and_deploy", {"terraform_dir": DEMO_INFRA_DIR})
            await _log(yield_event, "  -> Pre-Warm Successful. Mock production state created.", "success")
        except Exception as e:
            await _log(yield_event, f"  [WARN] Pre-warm apply failed: {str(e)[:200]}. Proceeding with clean state...", "warn")
```

### Acceptance Criteria
- Failed `checkout_branch` returns `False` and aborts the verification loop
- Pre-warm failure logs the actual error message
- `demo_loop.py` passes `py_compile`

---

## Work Package 6: Sandbox Isolation Improvements

**Priority**: High (security)
**Dependencies**: None
**Assignable independently**: ✅ Yes
**Estimated effort**: 1-2 days

### Problem

`engine/runner.py` `LocalStackConnector` only overrides 5 AWS services. Any Terraform config using other services (Lambda, SQS, SNS, CloudWatch, RDS, etc.) will either fail or attempt real AWS API calls.

Also, `server.py` `TerraformExecutor` has a more complete list (30+ services) but the two implementations don't share code.

### Step 6.1: Create shared constant

Create `engine/constants.py` (NEW FILE):

```python
"""Shared constants for the ShadowPlane engine."""

LOCALSTACK_SERVICES = [
    "apigateway", "apigatewayv2", "autoscaling", "backup",
    "cloudformation", "cloudfront", "cloudwatch", "cognitoidp",
    "cognitoidentity", "dynamodb", "ec2", "elasticache",
    "elasticsearch", "es", "firehose", "iam", "kinesis", "kms",
    "lambda", "opensearch", "redshift", "route53", "s3",
    "s3control", "sns", "sqs", "ssm", "stepfunctions", "sts",
]
```

### Step 6.2: Update `engine/runner.py`

Update `LocalStackConnector.setup_overrides()` to use the shared service list for generating the override HCL. Update `get_env_vars()` to include `AWS_ENDPOINT_URL` and per-service overrides:

```python
from engine.constants import LOCALSTACK_SERVICES

class LocalStackConnector(EmulatorConnector):
    def get_env_vars(self) -> Dict[str, str]:
        endpoint = os.getenv("AWS_ENDPOINT_URL", "http://127.0.0.1:4566")
        env = {
            "AWS_ACCESS_KEY_ID": "test",
            "AWS_SECRET_ACCESS_KEY": "test",
            "AWS_DEFAULT_REGION": "us-east-1",
            "AWS_ENDPOINT_URL": endpoint,
            "AWS_EC2_METADATA_DISABLED": "true",
        }
        for svc in ("S3", "DYNAMODB", "SQS", "SNS", "LAMBDA", "IAM", "STS", "EC2"):
            env[f"AWS_ENDPOINT_URL_{svc}"] = endpoint
        return env
    
    def setup_overrides(self, target_dir: str):
        endpoint = os.getenv("AWS_ENDPOINT_URL", "http://127.0.0.1:4566")
        endpoints_block = "\n".join(
            f'    {svc:<18} = "{endpoint}"' for svc in LOCALSTACK_SERVICES
        )
        override_hcl = f'''
provider "aws" {{
  access_key                  = "test"
  secret_key                  = "test"
  region                      = "us-east-1"
  s3_use_path_style           = true
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  endpoints {{
{endpoints_block}
  }}
}}
'''
        with open(os.path.join(target_dir, "localstack_override_providers.tf"), "w") as f:
            f.write(override_hcl)
```

### Step 6.3: Update `server.py` `TerraformExecutor`

Update `LOCALSTACK_OVERRIDE_TF` to also use the shared constant, or at minimum ensure both lists stay in sync.

### Acceptance Criteria
- `engine/constants.py` exists with `LOCALSTACK_SERVICES` list
- `runner.py` generates overrides for all 29 AWS services
- Both `runner.py` and `server.py` use the same service list
- `get_env_vars()` includes `AWS_ENDPOINT_URL` and per-service overrides
- All tests pass, both files pass `py_compile`

---

## Work Package 7: Slack Notification Fixes

**Priority**: Low
**Dependencies**: None
**Assignable independently**: ✅ Yes

### Problem

1. `engine/notifications.py` Slack buttons ("Approve & Merge", "Reject") are entirely decorative — no handler exists to process clicks.
2. Diff truncation shows only first 10 lines, potentially missing all actual changes.

### Instructions

1. Remove the `actions` block from the Slack message (lines 52-76 in `notifications.py`). Interactive buttons without a handler create a misleading UX. Replace with a simple footer:

```python
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "🔗 Review the full diff in the Pull Request. | ShadowPlane Autonomous Verification"
                    }
                ]
            }
```

2. Improve diff truncation. The current line-by-line index comparison (lines 13-20) produces nonsensical diffs when line counts change. Replace `_truncate_diff` with a `difflib`-based implementation:

```python
import difflib

def _truncate_diff(self, original: str, patched: str, max_lines: int = 30) -> str:
    orig_lines = original.splitlines(keepends=True)
    patch_lines = patched.splitlines(keepends=True)
    
    diff = list(difflib.unified_diff(
        orig_lines, patch_lines,
        fromfile="Original", tofile="Patched",
        lineterm=""
    ))
    
    if not diff:
        return "No differences detected."
    
    if len(diff) > max_lines:
        diff = diff[:max_lines] + [f"\n... ({len(diff) - max_lines} more lines truncated) ..."]
    
    return "".join(diff)
```

### Acceptance Criteria
- No interactive buttons in Slack messages
- Diff uses `difflib.unified_diff` for accurate output
- `notifications.py` passes `py_compile`

---

## Dependency Map

```
WP1 (CLI args)  ──→ can start immediately
WP2 (Landing page) ──→ can start immediately  
WP3 (Unified pipeline) ──→ depends on WP1
WP4 (MCP auth gate) ──→ can start immediately
WP5 (Git error handling) ──→ can start immediately
WP6 (Sandbox isolation) ──→ can start immediately
WP7 (Slack fixes) ──→ can start immediately
```

**Recommended execution order for a single agent**: WP1 → WP5 → WP4 → WP6 → WP7 → WP2 → WP3

**For parallel agents**: Assign WP3 to the strongest agent. WP1/WP4/WP5/WP6/WP7 can all run in parallel on separate agents. WP2 can go to any agent comfortable with TypeScript/React.

---

## Global Rules for All Work Packages

1. **Python path**: Use full path `C:\Users\syeda\AppData\Local\Programs\Python\Python313\python.exe` for all Python commands on this machine (Windows store alias causes dialog boxes)
2. **Never modify user infrastructure**: The `demo-infra/` directory is the only directory that may have its `main.tf` reset. User-supplied `--target-dir` paths must NEVER be modified by demo logic.
3. **Fail closed, not open**: Any missing tool (Checkov, etc.) must block the pipeline, not silently pass.
4. **Preserve comments**: Don't remove existing docstrings or comments unrelated to your changes.
5. **Test after every change**: Run `py_compile` on modified files and `python -m unittest discover -s . -p 'test_*.py'` after all changes.
6. **Line references may shift**: Phase 0 modified several files. Always read the file first to confirm current line numbers before editing.
