# ---- Build Stage ----
FROM python:3.10-slim as builder

# Use pipx to install poetry. This is a robust method for CI/CD and Docker.
RUN pip install pipx
RUN pipx install poetry==1.8.2
ENV PATH="/root/.local/bin:"

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.in-project true
RUN poetry install --no-root --no-dev --no-interaction

# ---- Final Stage ----
FROM python:3.10-slim

# Create and use a non-root user for better security.
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /home/appuser/app

# Copy files and set ownership to the non-root user.
COPY --from=builder --chown=appuser:appuser /app/.venv ./.venv
COPY --chown=appuser:appuser src/ .

# Now, switch to the non-root user.
USER appuser

# Make the venv python the default and add the app dir to PYTHONPATH.
ENV PATH="/home/appuser/app/.venv/bin:"
ENV PYTHONPATH="/home/appuser/app"

# Expose the port the app runs on.
EXPOSE 8000

# CRITICAL FIX: Use 'python -m uvicorn' to avoid shebang/line-ending issues.
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
