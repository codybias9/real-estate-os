# Use a specific version of the official Airflow image for reproducibility
FROM apache/airflow:2.9.3
# Install poetry, which is needed to install our project's Python dependencies
RUN pip install "poetry==1.8.2"
# Copy the project's dependency definitions into the image
COPY pyproject.toml poetry.lock ./
# Install the project's dependencies (like Scrapy) using poetry.
RUN poetry install --no-root --no-dev --no-interaction
# Copy the scraper source code so the Airflow workers can find and run it
COPY src/ ./src/
