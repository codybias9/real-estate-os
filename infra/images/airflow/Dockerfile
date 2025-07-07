# Use a specific version of the official Airflow image for reproducibility
FROM apache/airflow:2.9.3

# Switch to root user to install system-level dependencies
USER root

# Install poetry, which is needed to install our project's Python dependencies
RUN pip install "poetry==1.8.2"

# Switch back to the non-root 'airflow' user for security
USER airflow

# Copy the project's dependency definitions into the image
# The WORKDIR is already /opt/airflow in the base image
COPY pyproject.toml poetry.lock ./

# Install the project's dependencies (like Scrapy) using poetry.
# --no-root: Do not install the project itself, only its dependencies.
# --no-dev: Skip development dependencies like pytest.
# --no-interaction: Do not ask for interactive input.
RUN poetry install --no-root --no-dev --no-interaction

# Copy the scraper source code so the Airflow workers can find and run it
COPY src/ ./src/
