# Multi-stage Dockerfile for FastAPI API
# Production-ready with security best practices

# ============================================================================
# Stage 1: Base Python image with dependencies
# ============================================================================
FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# ============================================================================
# Stage 2: Build stage with dependencies
# ============================================================================
FROM base AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY api/requirements.txt .

# Install Python dependencies
RUN pip install --user --no-warn-script-location -r requirements.txt

# ============================================================================
# Stage 3: Runtime image
# ============================================================================
FROM base AS runtime

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY api/ /app/api/
COPY db/ /app/db/
COPY ml/ /app/ml/

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Run application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
