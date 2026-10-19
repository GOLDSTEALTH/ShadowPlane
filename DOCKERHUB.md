# ShadowPlane - IaC Containment Firewall & Verification Gateway

[![Version](https://img.shields.io/badge/version-2.1.0-blue.svg)](https://hub.docker.com/r/goldsteatlh/shadowplane) [![Docker Pulls](https://img.shields.io/docker/pulls/goldsteatlh/shadowplane.svg)](https://hub.docker.com/r/goldsteatlh/shadowplane) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/GOLDSTEALTH/ShadowPlane/blob/main/LICENSE) [![GitHub](https://img.shields.io/badge/GitHub-Repository-black?logo=github)](https://github.com/GOLDSTEALTH/ShadowPlane)

ShadowPlane is a deterministic Infrastructure as Code (IaC) containment firewall and verification gateway designed for Agentic DevOps.

Before autonomous AI agents (Claude Code, Cursor, Devin, GitHub Copilot) or engineers apply Terraform configurations to production cloud environments, ShadowPlane intercepts configurations and evaluates them inside an isolated container sandbox with fail-closed security and Change-Risk Intelligence.

---

## Problem Statement & Architecture

As AI coding agents author and modify Terraform HCL, two critical failure modes emerge:
1. **Destructive State Replacements**: An agent modifies a database or storage configuration that forces replacement (`forces new resource`), silently destroying databases or dropping buckets upon `apply`.
2. **Execution Breakouts**: Unvetted HCL with `local-exec` provisioners can escape the runner, access host credential files (`~/.aws/credentials`), and exfiltrate environment secrets.

ShadowPlane establishes an enforceable verification boundary:
* **Host-Isolated Sandboxing**: Executes Terraform inside disposable containers with stripped host credentials and network egress restricted to LocalStack.
* **Change-Risk Intelligence**: Pre-scans Terraform plan JSON to detect destructive actions on stateful resources (`aws_rds_cluster`, `aws_s3_bucket`, `aws_kms_key`) and flags IAM privilege broadening before `apply`.
* **Fail-Closed Security**: Enforces Checkov static analysis; missing scanner binaries or policy violations immediately block the gate.
* **Cryptographic Attestation**: Produces an immutable SHA-256 evidence hash and markdown attestation card for GitHub PRs and CI merge gates.
* **Circuit Breaker Safety**: Hard-blocks runaway AI agent retry loops after repeated failures.

---

## Quick Start

### 1. Pull the Image

```bash
docker pull goldsteatlh/shadowplane:latest
```

### 2. Verify Infrastructure Locally

Mount the Docker socket (allowing ShadowPlane to manage LocalStack emulation) and your infrastructure directory:

**Linux / macOS:**
```bash
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/infra:/app/infra \
  goldsteatlh/shadowplane:latest \
  --target-dir ./infra
```

**Windows (PowerShell):**
```powershell
docker run --rm `
  -v //var/run/docker.sock:/var/run/docker.sock `
  -v ${PWD}/infra:/app/infra `
  goldsteatlh/shadowplane:latest `
  --target-dir ./infra
```

### 3. Execution Exit Codes

ShadowPlane enforces deterministic exit codes designed for automated CI/CD runners:

| Exit Code | Status | Outcome |
|:---:|---|---|
| **0** | **Verification PASSED** | No destructive risks, security policies satisfied. Safe to deploy. |
| **1** | **Verification FAILED / BLOCKED** | Critical stateful deletion, security failure, or circuit breaker tripped. Pipeline blocked. |

---

## CI/CD Integration

Example GitHub Actions integration (`.github/workflows/verify-infra.yml`):

```yaml
name: Verify Infrastructure Changes

on:
  pull_request:
    branches: [ main ]

jobs:
  shadowplane-gate:
    name: ShadowPlane Verification Gateway
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Run ShadowPlane Verification
        uses: docker://goldsteatlh/shadowplane:2.1.0
        with:
          args: --target-dir ./infra --max-retries 4
        env:
          LOCALSTACK_AUTH_TOKEN: ${{ secrets.LOCALSTACK_AUTH_TOKEN }}
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

## Configuration & Environment Variables

| Variable | Description | Default |
|---|---|---|
| `SHADOWPLANE_RESET_TOKEN` | Required authorization token for resetting tripped circuit breakers via MCP | `""` |
| `LOCALSTACK_AUTH_TOKEN` | Optional LocalStack Pro / Enterprise activation token | `""` |
| `SLACK_WEBHOOK_URL` | Incoming webhook URL for automated ChatOps attestation cards | `""` |
| `GEMINI_API_KEY` | Optional Google Gemini API key for analysis engine | `""` |

---

## Supported Tags

* `2.1.0`, `latest`: Multi-stage build based on `python:3.13-slim` with pre-installed Terraform, LocalStack connectors, and Change-Risk Intelligence.

---

## References & Documentation

* GitHub Repository: [https://github.com/GOLDSTEALTH/ShadowPlane](https://github.com/GOLDSTEALTH/ShadowPlane)
* Architecture Specification: [WORKPLAN.md](https://github.com/GOLDSTEALTH/ShadowPlane/blob/main/WORKPLAN.md)
* Security Policy: [SECURITY.md](https://github.com/GOLDSTEALTH/ShadowPlane/blob/main/SECURITY.md)
* Issue Tracker: [GitHub Issues](https://github.com/GOLDSTEALTH/ShadowPlane/issues)
* License: MIT
