# ── CoinGPT Bot — Dockerfile ─────────────────────────────────────────────────
# Multi-stage build: keeps the final image lean (~120 MB)

# ── Stage 1: dependency builder ───────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build tools for any C-extension deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --prefix=/install --no-cache-dir -r requirements.txt


# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="CoinGPT Bot"
LABEL org.opencontainers.image.description="AI Crypto Telegram Bot"

# Non-root user for security
RUN useradd --create-home --shell /bin/bash botuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY --chown=botuser:botuser . .

USER botuser

# Prevent .pyc files and enable unbuffered stdout (important for logs)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
