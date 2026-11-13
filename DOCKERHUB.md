# ShadoPlane - IaC Containment Firewall & Verification Gateway

[![Version](https://img.shields.io/badge/version-2.1.0-blue.svg)](https://hub.docker.com/r/goldsteatlh/shadoplane) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/GOLDSTEALTH/ShadowPlane/blob/main/LICENSE) [![GitHub](https://img.shields.io/badge/GitHub-Repository-black?logo=github)](https://github.com/GOLDSTEALTH/ShadowPlane)

ShadoPlane is a deterministic Infrastructure as Code (IaC) containment firewall and verification gateway designed for Agentic DevOps.

Before autonomous AI agents (Claude Code, Cursor, Devin, GitHub Copilot Workspace) or platform engineers apply Terraform configurations to production cloud environments, ShadoPlane intercepts configurations and evaluates them inside an isolated container sandbox with fail-closed security and Change-Risk Intelligence.

---

## Problem Statement & Architecture

As AI coding agents author and modify Terraform HCL, two critical failure modes emerge:
1. **Destructive State Replacements**: An agent modifies a database or storage configuration that forces replacement (`forces new resource`), silently destroying databases or dropping buckets upon `apply`.
2. **Execution Breakouts**: Unvetted HCL with `local-exec` provisioners can escape the runner, access host credential files (`~/.aws/credentials`), and exfiltrate environment secrets.

```
PR / Agent HCL ──> [ShadoPlane Verification Gateway]
                          │
                          ▼
         ┌───────────────────────────────────┐
         │ Stage 1: Terraform Init           │
         │  • Syntax validation              │
         │  • Provider initialization        │
         └─────────────────┬─────────────────┘
                           │
                           ▼
         ┌───────────────────────────────────┐
         │ Stage 2: Fail-Closed Security     │
         │  • Checkov 3.x static analysis    │
         │  • Blocks on policy violations    │
         └─────────────────┬─────────────────┘
                           │
                           ▼
         ┌───────────────────────────────────┐
         │ Stage 3: Change-Risk Intelligence │
         │  • Terraform plan -json analysis  │
         │  • Detects stateful drops & IAM   │
         └─────────────────┬─────────────────┘
                           │
                           ▼
         ┌───────────────────────────────────┐
         │ Stage 4: LocalStack Deploy & Hash │
         │  • Sandbox emulation apply        │
         │  • SHA-256 evidence attestation   │
         └─────────────────┬─────────────────┘
                           │
                           ▼
        [Cryptographic Attestation & Evidence Pack]
         (Exit 0: Safe to Deploy | Exit 1: Gate Blocked)
```

ShadoPlane establishes an enforceable verification boundary:
* **Host-Isolated Sandboxing**: Executes Terraform inside disposable containers with stripped host credentials and network egress restricted to LocalStack.
* **Change-Risk Intelligence**: Pre-scans Terraform plan JSON to detect destructive actions on stateful resources (`aws_rds_cluster`, `aws_s3_bucket`, `aws_kms_key`, `aws_dynamodb_table`) and flags IAM privilege broadening before `apply`.
* **Fail-Closed Security**: Enforces Checkov static analysis; missing scanner binaries or policy violations immediately block the gate.
* **Cryptographic Attestation**: Produces an immutable SHA-256 evidence hash and markdown attestation card for GitHub PRs and CI merge gates.
* **Circuit Breaker Safety**: Hard-blocks runaway AI agent retry loops after 4 consecutive failures within a 300s sliding window.

---

## Quick Start

### 1. Pull the Image

```bash
docker pull goldsteatlh/shadoplane:latest
# Or pin to specific release tag:
docker pull goldsteatlh/shadoplane:2.1.0
```

### 2. Verify Infrastructure Locally

Mount the Docker socket (allowing ShadoPlane to manage LocalStack emulation) and your infrastructure directory:

**Linux / macOS:**
```bash
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/infra:/workspace \
  goldsteatlh/shadoplane:2.1.0 \
  --target-dir /workspace \
  --output-json /workspace/attestation.json
```

**Windows (PowerShell):**
```powershell
docker run --rm `
  -v //var/run/docker.sock:/var/run/docker.sock `
  -v ${PWD}/infra:/workspace `
  goldsteatlh/shadoplane:2.1.0 `
  --target-dir /workspace `
  --output-json /workspace/attestation.json
```

### 3. CLI Command Options

```text
usage: shadoplane [-h] [--target-dir TARGET_DIR] [--output-json OUTPUT_JSON]
                  [--no-docker] [--pr PR] [--demo]
                  [--max-retries MAX_RETRIES] [--ai-model AI_MODEL]
                  [--ai-base-url AI_BASE_URL] [--version]

options:
  --target-dir TARGET_DIR   Path to the Terraform directory to verify (default: ./demo-infra)
  --output-json OUTPUT_JSON Path to export the signed JSON attestation pack
  --no-docker               Force host-level execution instead of Docker container runner
  --pr PR                   Optional PR number for Slack notifications
  --demo                    Run legacy interactive self-healing demo loop
  --version                 Show the version and exit
```

### 4. Execution Exit Codes

ShadoPlane enforces deterministic exit codes designed for automated CI/CD runners:

| Exit Code | Status | Outcome |
|:---:|---|---|
| **0** | **Verification PASSED** | No destructive risks, security policies satisfied. Safe to deploy. |
| **1** | **Verification FAILED / BLOCKED** | Critical stateful deletion, security failure, or circuit breaker tripped. Pipeline blocked. |

---

## CI/CD Integration

### Option A: Using the Docker Container Directly

```yaml
name: Verify Infrastructure Changes

on:
  pull_request:
    branches: [ main ]

jobs:
  shadoplane-gate:
    name: ShadoPlane Verification Gateway
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Run ShadoPlane Verification
        uses: docker://goldsteatlh/shadoplane:2.1.0
        with:
          args: --target-dir ./infra --output-json attestation.json
        env:
          LOCALSTACK_AUTH_TOKEN: ${{ secrets.LOCALSTACK_AUTH_TOKEN }}
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### Option B: Using the GitHub Action (`action.yml`)

```yaml
      - name: Run ShadoPlane Action
        uses: GOLDSTEALTH/ShadowPlane@v2.1.0
        with:
          target-dir: ./infra
          output-json: attestation.json
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

## Configuration & Environment Variables

| Variable | Description | Default |
|---|---|---|
| `SHADOWPLANE_RESET_TOKEN` | Required authorization token for resetting tripped circuit breakers via MCP | `""` |
| `LOCALSTACK_AUTH_TOKEN` | Optional LocalStack Pro / Enterprise activation token | `""` |
| `SLACK_WEBHOOK_URL` | Incoming webhook URL for automated ChatOps attestation cards | `""` |
| `GITHUB_STEP_SUMMARY` | Automatically populated by GitHub Actions to display attestation card | `""` |
| `GEMINI_API_KEY` | Optional API key when running interactive demo mode | `""` |

---

## Supported Tags

* `2.1.0`, `latest`: Hardened multi-stage build based on `python:3.13-slim` with pre-installed Terraform v1.12.1, Checkov 3.4.5, LocalStack connectors, and Change-Risk Intelligence.

---

## References & Documentation

* GitHub Repository: [https://github.com/GOLDSTEALTH/ShadowPlane](https://github.com/GOLDSTEALTH/ShadowPlane)
* Security Policy: [SECURITY.md](https://github.com/GOLDSTEALTH/ShadowPlane/blob/main/SECURITY.md)
* Issue Tracker: [GitHub Issues](https://github.com/GOLDSTEALTH/ShadowPlane/issues)
* License: MIT
