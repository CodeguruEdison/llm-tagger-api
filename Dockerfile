# ─────────────────────────────────────────────
# Stage 1: base
# Shared base image for all stages
# ─────────────────────────────────────────────
FROM python:3.12-slim AS base

# Prevents Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
# Ensures stdout/stderr are unbuffered (important for Docker logs)
ENV PYTHONUNBUFFERED=1
# uv install location
ENV PATH="/root/.local/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv — fast Python package manager (in /usr/local so entrypoint as tagger can run it)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    ln -sf /usr/local/bin/uv /usr/local/bin/uvx 2>/dev/null || true

WORKDIR /app

# ─────────────────────────────────────────────
# Stage 2: dependencies
# Install all Python dependencies
# Cached separately from app code so rebuilds
# are fast when only code changes
# ─────────────────────────────────────────────
FROM base AS dependencies

# Copy dependency files first (for layer caching)
COPY pyproject.toml uv.lock ./

# Install production dependencies only (not the project itself — src/ not copied yet)
RUN uv sync --no-dev --no-install-project --frozen

# ─────────────────────────────────────────────
# Stage 3: development
# Includes dev dependencies, hot reload
# Used in docker-compose for local development
# ─────────────────────────────────────────────
FROM dependencies AS development

# Copy source code first so the project can be installed
COPY src/ ./src/
COPY tests/ ./tests/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY scripts/entrypoint.sh ./scripts/entrypoint.sh

# Install ALL dependencies including dev + the project itself
RUN uv sync --frozen

# Non-root user for security (even in dev)
RUN groupadd -r tagger && useradd -r -g tagger tagger
RUN chown -R tagger:tagger /app && chmod +x ./scripts/entrypoint.sh
USER tagger

EXPOSE 8000

# Run migrations then start the app
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["uv", "run", "uvicorn", "tagging.api.app:app", \
    "--host", "0.0.0.0", \
    "--port", "8000", \
    "--reload", \
    "--reload-dir", "src"]

# ─────────────────────────────────────────────
# Stage 4: production
# Minimal image, no dev tools, non-root user
# Optimized for 17k req/sec:
#   - multiple uvicorn workers
#   - uvloop for async performance
#   - httptools for HTTP parsing
# ─────────────────────────────────────────────
FROM dependencies AS production

# Copy only production source
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Install the project itself (prod deps already in venv from dependencies stage)
RUN uv sync --no-dev --frozen

# Non-root user — security best practice
RUN groupadd -r tagger && useradd -r -g tagger tagger
RUN chown -R tagger:tagger /app
USER tagger

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Multiple workers for production scale
# Formula: (2 × CPU cores) + 1
# Override with WORKERS env var in Kubernetes
CMD ["sh", "-c", "uv run uvicorn tagging.api.app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers ${WORKERS:-4} \
    --loop uvloop \
    --http httptools \
    --log-level ${LOG_LEVEL:-info}"]
