# ============================================================================
# ShadowPlane — Production Dockerfile
# ============================================================================
# Multi-stage build for a lean, production-ready container.
#
# Usage:
#   docker build -t shadowplane .
#   docker run --rm -v /var/run/docker.sock:/var/run/docker.sock shadowplane
#   docker run --rm shadowplane --target-dir /workspace/infra --max-retries 3
#
# GitHub Actions:
#   - uses: docker://shadowplane:latest
#     with:
#       args: --target-dir ./infra
# ============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder — install Python dependencies
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --target /build/deps -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2: Runtime — lean production image
# ---------------------------------------------------------------------------
FROM python:3.13-slim

LABEL maintainer="GOLDSTEALTH"
LABEL description="ShadowPlane — Autonomous Infrastructure Verification Pipeline"
LABEL org.opencontainers.image.source="https://github.com/GOLDSTEALTH/ShadowPlane"

# -- System dependencies ----------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# -- Install Terraform -------------------------------------------------------
ARG TERRAFORM_VERSION=1.12.1
RUN curl -fsSL "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip" \
    -o /tmp/terraform.zip \
    && unzip /tmp/terraform.zip -d /usr/local/bin/ \
    && rm /tmp/terraform.zip \
    && terraform version

# -- Install Docker CLI (for LocalStack container management) ----------------
RUN curl -fsSL https://get.docker.com | sh \
    || echo "Docker CLI installation skipped — mount docker.sock at runtime"

# -- Python dependencies from builder stage ----------------------------------
COPY --from=builder /build/deps /usr/local/lib/python3.13/site-packages/

# -- Application code --------------------------------------------------------
WORKDIR /app

# Copy only what's needed for the headless CLI pipeline
COPY VERSION .
COPY cli.py .
COPY demo_loop.py .
COPY server.py .
COPY demo-infra/ ./demo-infra/

# Copy optional .env (will be overridden by runtime env vars in CI)
COPY .env* ./

# -- Environment defaults ----------------------------------------------------
ARG VERSION="unknown"
ENV SHADOWPLANE_VERSION=${VERSION}
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV AWS_DEFAULT_REGION=us-east-1
# Note: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY mock credentials
# are injected dynamically at runtime in server.py to avoid baking secret-pattern
# variable names into image layer metadata (satisfies SecretsUsedInArgOrEnv check).

# -- Healthcheck -------------------------------------------------------------
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import server; print('ok')" || exit 1

# -- Entrypoint --------------------------------------------------------------
ENTRYPOINT ["python", "cli.py"]
CMD ["--target-dir", "./demo-infra"]
