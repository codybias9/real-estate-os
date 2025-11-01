FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ src/

# Create directories for models
RUN mkdir -p /models

# Set Python path
ENV PYTHONPATH=/app/src

# Default entrypoint
ENTRYPOINT ["python", "-m", "scoring_agent.scoring_agent"]
