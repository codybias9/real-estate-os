# =============================================================================
# Base Stage - Common dependencies
# =============================================================================
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # PostgreSQL client
    libpq-dev \
    # PDF generation dependencies (WeasyPrint)
    python3-dev \
    python3-pip \
    python3-cffi \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    # Build tools
    gcc \
    g++ \
    make \
    # Other utilities
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# =============================================================================
# Poetry Stage - Install poetry and dependencies
# =============================================================================
FROM base as poetry

# Install poetry
RUN pip install poetry==1.8.2

# Copy poetry files
COPY pyproject.toml poetry.lock ./

# Configure poetry to not create virtual env (we're in container)
RUN poetry config virtualenvs.create false

# =============================================================================
# Development Stage
# =============================================================================
FROM poetry as development

# Install all dependencies including dev dependencies
RUN poetry install --no-interaction --no-ansi

# Copy application code
COPY . .

# Expose ports
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# =============================================================================
# Production Dependencies Stage
# =============================================================================
FROM poetry as prod-deps

# Install only production dependencies
RUN poetry install --no-interaction --no-ansi --no-dev --no-root

# =============================================================================
# Production Stage
# =============================================================================
FROM base as production

# Copy installed dependencies from prod-deps stage
COPY --from=prod-deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=prod-deps /usr/local/bin /usr/local/bin

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create necessary directories
RUN mkdir -p /app/logs /app/tmp && \
    chown -R appuser:appuser /app

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Run with gunicorn for production
CMD ["gunicorn", "api.main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]
