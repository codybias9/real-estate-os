# ---- Build Stage ----
FROM python:3.10-slim as builder
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VERSION=1.8.2
RUN python -m venv .venv && .venv/bin/pip install poetry==$POETRY_VERSION
ENV PATH="/home/appuser/.venv/bin:$PATH"
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /home/appuser
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --no-dev --no-interaction
# ---- Final Stage ----
FROM python:3.10-slim
RUN useradd --create-home --shell /bin/bash appuser
USER appuser
WORKDIR /home/appuser
COPY --from=builder /home/appuser/.venv ./.venv
COPY src/ ./src
ENV PATH="/home/appuser/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
