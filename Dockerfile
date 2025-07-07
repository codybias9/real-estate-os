# ---- Build Stage ----
FROM python:3.10-slim as builder

# Install poetry
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VERSION=1.8.2
RUN python -m venv  && /bin/pip install poetry==
ENV PATH="/bin:"

# Set up a non-root user
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /home/appuser

# Install dependencies
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --no-dev --no-interaction

# ---- Final Stage ----
FROM python:3.10-slim

# Create and use a non-root user
RUN useradd --create-home --shell /bin/bash appuser
USER appuser
WORKDIR /home/appuser

# Copy virtual environment and application code from the builder stage
COPY --from=builder /home/appuser/.venv ./.venv
COPY src/ ./src

# Make the venv python the default
ENV PATH="/home/appuser/.venv/bin:"

# Expose the port the app runs on
EXPOSE 8000

# Run the API with Uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
