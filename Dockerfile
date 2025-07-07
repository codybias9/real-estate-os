# ---- Build Stage ----
FROM python:3.10-slim as builder

# Use pipx to install poetry. This is a robust method for CI/CD and Docker.
RUN pip install pipx
RUN pipx install poetry==1.8.2

# Add pipx-injected binaries to the PATH.
ENV PATH="/root/.local/bin:"

WORKDIR /app
COPY pyproject.toml poetry.lock ./

# Install dependencies into a virtual environment.
RUN poetry install --no-root --no-dev --no-interaction

# ---- Final Stage ----
FROM python:3.10-slim

# Create and use a non-root user for better security.
RUN useradd --create-home --shell /bin/bash appuser
USER appuser
WORKDIR /home/appuser/app

# Copy the virtual environment and application code from the builder stage.
COPY --from=builder /app/.venv ./.venv
COPY src/ ./src

# Make the venv python the default, ensuring our app uses the installed dependencies.
ENV PATH="/home/appuser/app/.venv/bin:"

# Expose the port the app runs on.
EXPOSE 8000

# Run the API with Uvicorn.
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
