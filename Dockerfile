# ---- Build Stage ----
FROM python:3.10-slim as builder

# Install Poetry using the official installer, which is the recommended best practice.
ENV POETRY_VERSION=1.8.2
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:"

# Set up a non-root user for better security.
WORKDIR /app
COPY pyproject.toml poetry.lock ./

# Install dependencies into a virtual environment.
RUN poetry install --no-root --no-dev --no-interaction

# ---- Final Stage ----
FROM python:3.10-slim

# Create and use a non-root user.
RUN useradd --create-home --shell /bin/bash appuser
USER appuser
WORKDIR /home/appuser/app

# Copy virtual environment from the builder stage.
COPY --from=builder /app/.venv ./.venv
# Copy application code.
COPY src/ ./src

# Make the venv python the default, ensuring our app uses the installed dependencies.
ENV PATH="/home/appuser/app/.venv/bin:"

# Expose the port the app runs on.
EXPOSE 8000

# Run the API with Uvicorn.
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
