# We use the official Airflow image as a base
FROM apache/airflow:2.9.3

# Switch to root to install system dependencies and configure sudo
USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends sudo libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libatspi2.0-0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Grant passwordless sudo to the airflow user
RUN echo "airflow ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/airflow && \
    chmod 0440 /etc/sudoers.d/airflow

# Switch back to the airflow user
USER airflow

# Copy the Scrapy project into the image
COPY --chown=airflow:airflow src/ /opt/airflow/src/

# Copy the poetry dependency files
COPY --chown=airflow:airflow pyproject.toml poetry.lock /opt/airflow/

# Install poetry, project dependencies, and Playwright's browsers
# The 'sudo' command used by playwright will now work without a password.
RUN pip install "poetry==1.8.2" && \
    cd /opt/airflow && \
    poetry install --no-root --no-dev && \
    poetry run playwright install --with-deps
