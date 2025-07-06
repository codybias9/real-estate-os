FROM python:3.10-slim

WORKDIR /app

# Install Python dependencies
COPY agents/requirements.txt .
RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy all agent code
COPY agents/ ./agents/

# Copy DAGs into the expected Airflow path
COPY dags/ /opt/airflow/dags/
