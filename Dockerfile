# syntax=docker/dockerfile:1.7

# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: build the Tailwind CSS bundle using a slim Node image.
# Thrown away after the artifact is produced.
# ─────────────────────────────────────────────────────────────────────────────
FROM node:20-alpine AS css-builder

WORKDIR /build

# Install dependencies first for layer caching.
COPY backend/package.json backend/package-lock.json ./
RUN npm ci --no-audit --no-fund

# Tailwind needs the templates and the config to scan for class names.
COPY backend/tailwind.config.js ./
COPY backend/app/templates/ ./app/templates/
COPY backend/app/static/css/app.css ./app/static/css/app.css

RUN npx tailwindcss \
        --config tailwind.config.js \
        --input app/static/css/app.css \
        --output app/static/css/app.compiled.css \
        --minify

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: runtime image. Python only — no Node, no npm, no Tailwind tooling.
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps. libgomp1 is required by statsmodels / scipy-style wheels.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        libgomp1 \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first so this layer is cached independently of source.
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Application code (templates, static assets, etc.).
COPY backend/ ./

# Pull the pre-built CSS bundle from the builder stage.
COPY --from=css-builder /build/app/static/css/app.compiled.css /app/app/static/css/app.compiled.css

# Persistent SQLite directory; mounted as a GCP persistent disk in production.
RUN mkdir -p /app/data \
    && useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/healthz || exit 1

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
