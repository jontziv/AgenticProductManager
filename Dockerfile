# ── Frontend build stage ──────────────────────────────────────────────────────
FROM node:20-slim AS frontend-builder

WORKDIR /front

# Install Node deps first (layer-cached)
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# Copy all frontend source (context is repo root)
COPY index.html tsconfig.json tsconfig.node.json vite.config.ts postcss.config.mjs ./
COPY src/ ./src/

# Build React app → /front/dist
RUN npm run build


# ── Python deps build stage ───────────────────────────────────────────────────
FROM python:3.12-slim AS python-builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Runtime libs only
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Python packages
COPY --from=python-builder /install /usr/local

# Backend application code
COPY backend/app/ ./app/
COPY backend/worker/ ./worker/

# Built React frontend — served as static files by FastAPI
COPY --from=frontend-builder /front/dist ./static/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/healthz || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
