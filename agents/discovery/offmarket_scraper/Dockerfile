FROM python:3.10-slim

# install wget for HEALTHCHECK
RUN apt-get update && apt-get install -y wget --no-install-recommends && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY health.py .
COPY src/ src/
EXPOSE 5000

# single‐line exec‐form HEALTHCHECK
HEALTHCHECK --interval=30s --timeout=3s CMD ["wget","--quiet","--spider","http://localhost:5000/healthz"] || exit 1

# use ENTRYPOINT so nothing is wrapped in sh
ENTRYPOINT ["gunicorn", "--bind", "0.0.0.0:5000", "health:app"]
