# ShadowPlane - IaC Containment Firewall & Verification Gateway

![Version](https://img.shields.io/badge/version-2.1.0-blue.svg) ![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg) ![License](https://img.shields.io/badge/license-MIT-green.svg) ![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)

ShadowPlane is a deterministic IaC Containment Firewall and Verification Gateway designed for Agentic DevOps.

## About ShadowPlane

As AI coding agents (Claude Code, Cursor, Devin, GitHub Copilot Workspace) gain the ability to generate and modify infrastructure as code, the risk of an agent hallucinating invalid configurations, introducing security backdoors, or deleting stateful production resources skyrockets.

ShadowPlane acts as an **IaC Verification Gateway & Execution Firewall**:
1. **Isolated Docker Sandboxing**: Executes Terraform inside disposable, rootless Docker sandbox containers with host credentials stripped and network egress locked to LocalStack, neutralizing `local-exec` escape risks.
2. **Fail-Closed Security**: Evaluates configurations against Checkov static analysis policies. Missing tools or security violations fail closed.
3. **Change-Risk Intelligence**: Inspects plan JSON to proactively block destructive stateful resource drops (e.g. `aws_s3_bucket`, `aws_db_instance`, `aws_kms_key`) and alert on IAM privilege broadening.
4. **Cryptographic Attestation**: Produces a tamper-evident SHA-256 evidence hash and markdown attestation pack for PR reviews and CI merge gates.
5. **Circuit Breaker Safety**: Enforces sliding-window failure counters to physically halt runaway agent retry loops.

## The Architecture

```
PR / Agent HCL ──> [ShadowPlane Gateway]
                         │
                         ▼
        ┌───────────────────────────────────┐
        │ Hardened Docker Sandbox Container │
        │  • Stripped host AWS credentials  │
        │  • Terraform / OpenTofu Runner    │
        │  • Network locked to LocalStack   │
        └─────────────────┬─────────────────┘
                          │
                          ▼
        ┌───────────────────────────────────┐
        │  Change-Risk & Policy Engine      │
        │  • Fail-closed Checkov scanner    │
        │  • Stateful deletion detector     │
        │  • IAM privilege creep analyzer   │
        └─────────────────┬─────────────────┘
                          │
                          ▼
       [Cryptographic Attestation & Evidence Pack]
        (SHA-256 Hash • PR Comments • CI Exit Codes)
```

1. **Contain & Sandbox**: Mounts the target directory into an ephemeral Docker container with mock credentials (`AWS_ACCESS_KEY_ID=test`).
2. **Init & Security Scan**: Executes `terraform init` and fail-closed Checkov static analysis.
3. **Change-Risk Analysis**: Analyzes `terraform plan -json` to flag destructive deletions and IAM broadening before apply.
4. **Deploy & Attest**: Deploys to LocalStack, computes an immutable SHA-256 evidence hash, and renders an Attestation Pack.
5. **Enforce Gate**:
   - **`sys.exit(0)`**: Verification PASSED. Risk verified safe; attestation approved.
   - **`sys.exit(1)`**: Verification FAILED or BLOCKED. Critical risk detected or breaker tripped; merge pipeline blocked.

## Install

### One-liner (recommended)

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/GOLDSTEALTH/ShadowPlane/main/install.ps1 | iex
```

**Linux / macOS:**
```bash
curl -sSL https://raw.githubusercontent.com/GOLDSTEALTH/ShadowPlane/main/install.sh | bash
```

### From PyPI

```bash
pip install shadowplane
```

### From source

```bash
git clone https://github.com/GOLDSTEALTH/ShadowPlane.git
cd ShadowPlane
pip install -e .
```

### Requirements

- Python 3.10+
- Docker (for LocalStack sandbox)
- Terraform or OpenTofu
- Git

## CLI Commands

After installation, three commands are available globally from any terminal:

```
shadowplane             Run the verification pipeline
shadowplane-server      Start the MCP gateway server
shadowplane-engine      Run the enterprise engine
```

### `shadowplane` — Verification Pipeline

```bash
# Verify infrastructure in a directory
shadowplane --target-dir ./my-infra

# Set max execution attempts before circuit breaker trips
shadowplane --target-dir ./infra --max-retries 3

# Check version
shadowplane --version
```

**Exit codes:**
| Code | Meaning |
|------|---------|
| `0` | Verification PASSED — safe to deploy |
| `1` | Verification FAILED — pipeline blocked |

### `shadowplane-server` — MCP Gateway

Starts the FastMCP server exposing tools for AI agents:

```bash
shadowplane-server
```

**Available MCP tools:**
| Tool | Description |
|------|-------------|
| `clone_and_deploy` | Deploy Terraform configs in a LocalStack sandbox |
| `read_sandbox_logs` | Read deployment logs by ID |
| `reset_circuit_breaker` | Reset the safety breaker after human intervention |

### `shadowplane-engine` — Enterprise Engine

Runs the full Verification Gateway pipeline with Change-Risk Intelligence, Checkov security scanning, and Slack notifications:

```bash
shadowplane-engine --target-dir ./infra --pr 42
```

## Circuit Breaker (Safety)

ShadowPlane includes a built-in circuit breaker to prevent runaway retry loops. This is critical when AI agents call `clone_and_deploy` in a loop.

**How it works:**
- After **4 consecutive failures** for the same Terraform directory, the breaker **trips**
- All subsequent calls return a hard-stop message instead of Terraform output:
  ```
  SYSTEM OVERRIDE: MAX RETRIES EXCEEDED. YOU MUST STOP EXECUTING.
  ```
- The breaker stays tripped until a human resets it:
  ```bash
  # Via MCP tool
  reset_circuit_breaker("/path/to/infra")
  ```

**Why this matters:** Without this, an LLM agent can enter an infinite feedback loop — we observed **839 consecutive failed retries** before implementing this safeguard.

## Quick Start (GitHub Actions)

ShadowPlane is completely headless and Dockerized. You can drop it directly into your `.github/workflows/deploy.yml` file to gatekeep your Terraform deployments.

```yaml
name: Deploy Infrastructure

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v3

      - name: ShadowPlane Gatekeeper
        uses: docker://goldsteatlh/shadowplane:2.1.0
        with:
          args: --target-dir ./infra --max-retries 5
        env:
          # Optional: LocalStack Pro token for advanced AWS features
          LOCALSTACK_AUTH_TOKEN: ${{ secrets.LOCALSTACK_AUTH_TOKEN }}
```

## Local Execution (Docker)

To run the gatekeeper locally on your workstation to test infrastructure patches, just run the Docker image. You must bind-mount the Docker socket so ShadowPlane can spin up its LocalStack sandbox.

```bash
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/infra:/app/infra \
  goldsteatlh/shadowplane:2.1.0 \
  --target-dir ./infra
```

## Versioning

ShadowPlane strictly follows [Semantic Versioning (SemVer)](https://semver.org/). 

The current version is defined in the `VERSION` file. When referencing ShadowPlane in your CI/CD pipelines, **always pin your workflows to a specific major/minor tag** (e.g., `docker://goldsteatlh/shadowplane:2.1.0`) to prevent breaking changes from interrupting your deployments.

## Development

Use the included Makefile for local development:
- `make build`: Builds the Docker image based on the `VERSION` file.
- `make run`: Runs the container locally against `./demo-infra`.
- `make test`: Tests the Python CLI syntax.

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run full unit test suite (36 tests)
python -m unittest discover -s . -p "test_*.py" -v
```
