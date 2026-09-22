# ShadowPlane

![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)
![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)

ShadowPlane is an autonomous CI/CD gatekeeper designed for Agentic DevOps.

## About ShadowPlane

As AI coding agents gain the ability to generate and deploy infrastructure (Terraform, AWS CDK, etc.), the risk of an AI hallucinating an invalid configuration and bringing down production skyrockets. 

ShadowPlane solves this by providing a deterministic, secure sandbox that intercepts these deployments. Before any infrastructure code reaches your real cloud environment, ShadowPlane provisions it inside an isolated **LocalStack** container. If the deployment fails (due to a bad bucket name, malformed IAM policy, etc.), ShadowPlane's AI self-healing engine parses the Terraform logs, patches the `.tf` files, and tries again.

It strictly enforces system exit codes (`0` for Pass, `1` for Fail), ensuring your CI/CD runner knows exactly when it is safe to proceed to production.

## The Architecture

1. **Intercept & Sandbox**: The CLI targets a directory and triggers an ephemeral LocalStack sandbox using Docker.
2. **Execute**: It runs `terraform init` and `terraform apply`.
3. **Analyze & Self-Heal**: If it encounters an AWS API error, it reads the sandbox stderr, matches known fix patterns, and rewrites the Terraform code autonomously.
4. **Circuit Breaker**: A built-in safety net prevents runaway retry loops — after 4 consecutive failures, execution is hard-blocked until a human intervenes.
5. **Gatekeep**: 
   - **`sys.exit(0)`**: Blast radius contained. Infrastructure verified.
   - **`sys.exit(1)`**: Maximum retries exhausted. The CI pipeline is hard-blocked.

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

# Set max self-healing retries
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

Runs the full AI-powered pipeline with Gemini integration, Checkov security scanning, and Slack notifications:

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
        uses: docker://goldstealth/shadowplane:0.1.0
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
  goldstealth/shadowplane:0.1.0 \
  --target-dir ./infra
```

## Versioning

ShadowPlane strictly follows [Semantic Versioning (SemVer)](https://semver.org/). 

The current version is defined in the `VERSION` file. When referencing ShadowPlane in your CI/CD pipelines, **always pin your workflows to a specific major/minor tag** (e.g., `docker://goldstealth/shadowplane:0.1.0`) to prevent breaking changes from interrupting your deployments.

## Development

Use the included Makefile for local development:
- `make build`: Builds the Docker image based on the `VERSION` file.
- `make run`: Runs the container locally against `./demo-infra`.
- `make test`: Tests the Python CLI syntax.

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run circuit breaker tests
python -m unittest test_circuit_breaker -v
```
