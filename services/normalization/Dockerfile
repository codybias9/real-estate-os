# Dockerfile for Address Normalization Service with libpostal
FROM python:3.11-slim

# Install build dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    autoconf \
    automake \
    libtool \
    pkg-config \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Build and install libpostal
WORKDIR /tmp
RUN git clone https://github.com/openvenues/libpostal && \
    cd libpostal && \
    ./bootstrap.sh && \
    ./configure --datadir=/usr/local/share/libpostal && \
    make -j$(nproc) && \
    make install && \
    ldconfig && \
    cd .. && \
    rm -rf libpostal

# Install Python libpostal bindings
RUN pip install --no-cache-dir postal

# Install application dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create app directory
WORKDIR /app

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
