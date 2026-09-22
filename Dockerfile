# ============================================================================
# ShadowPlane — Production Dockerfile
# ============================================================================
# Multi-stage build for a lean, production-ready container.
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
    ca-certificates \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# -- Install Terraform (Verified) --------------------------------------------
ARG TERRAFORM_VERSION=1.12.1
# Expected SHA256 checksum for Terraform 1.12.1 on Linux AMD64
ARG TERRAFORM_SHA256="4d7db8b7a0f6b3e9a5c8df59f1c0ea5c1b63e8a71d87e0e47d10cbe7a13c38b2"

RUN curl -fsSL "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip" -o /tmp/terraform.zip \
    && echo "${TERRAFORM_SHA256} /tmp/terraform.zip" | sha256sum -c - \
    && unzip /tmp/terraform.zip -d /usr/local/bin/ \
    && rm /tmp/terraform.zip \
    && terraform version

# -- Least Privilege (Non-Root User) -----------------------------------------
RUN groupadd -r shadowplane && useradd -r -g shadowplane -d /app -s /sbin/nologin shadowplane \
    && mkdir -p /app \
    && chown -R shadowplane:shadowplane /app

# -- Python dependencies from builder stage ----------------------------------
COPY --from=builder /build/deps /usr/local/lib/python3.13/site-packages/

# -- Application code --------------------------------------------------------
WORKDIR /app

# Copy application files and set ownership
COPY --chown=shadowplane:shadowplane VERSION .
COPY --chown=shadowplane:shadowplane cli.py .
COPY --chown=shadowplane:shadowplane demo_loop.py .
COPY --chown=shadowplane:shadowplane server.py .
COPY --chown=shadowplane:shadowplane main.py .
COPY --chown=shadowplane:shadowplane circuit_breaker.py .
COPY --chown=shadowplane:shadowplane engine/ ./engine/
COPY --chown=shadowplane:shadowplane demo-infra/ ./demo-infra/

# SECURITY FIX: Explicitly DO NOT copy `.env*` to prevent baking secrets into layers.
# Env vars should be passed dynamically at runtime via `docker run --env-file .env`

# -- Environment defaults ----------------------------------------------------
ARG VERSION="unknown"
ENV SHADOWPLANE_VERSION=${VERSION}
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV AWS_DEFAULT_REGION=us-east-1

# Drop to non-root user
USER shadowplane

# -- Healthcheck -------------------------------------------------------------
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import server; print('ok')" || exit 1

# -- Entrypoint --------------------------------------------------------------
ENTRYPOINT ["python", "cli.py"]
CMD ["--target-dir", "./demo-infra"]
