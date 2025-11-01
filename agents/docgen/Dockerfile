FROM python:3.10-slim

# Install system dependencies for WeasyPrint and Node.js for MJML
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    # WeasyPrint dependencies
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    # Node.js for MJML CLI
    curl \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Install Node.js 18.x
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install MJML globally
RUN npm install -g mjml

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ src/

# Copy templates directory (will be mounted in production)
RUN mkdir -p /app/templates

# Set Python path
ENV PYTHONPATH=/app/src

# Default entrypoint
ENTRYPOINT ["python", "-m", "docgen_agent.docgen_agent"]
