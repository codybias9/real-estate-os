# real-estate-os

This project is a real estate data processing and outreach platform orchestrated by Apache Airflow.

## Local Development Setup

This project uses **Docker Compose** for a lightweight local development environment. This avoids the overhead of running a full Kubernetes cluster on your machine.

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Python 3.10+](https://www.python.org/)
- [Poetry](https://python-poetry.org/) for Python dependency management.

### 1. Initial Setup

First, clone the repository and navigate into the project directory.

```bash
git clone https://github.com/codybias9/real-estate-os.git
cd real-estate-os
```

### 2. Install Python Dependencies

This project uses Poetry to manage dependencies. Run the following to create a virtual environment and install the required packages from `pyproject.toml`.

```bash
poetry install
```

### 3. Set up Airflow Environment

We use the official Airflow Docker Compose file for local development.

1.  **Create necessary folders and a `.env` file:**
    ```powershell
    mkdir -p ./dags, ./logs, ./plugins, ./config
    echo "AIRFLOW_UID=$(id -u)" > .env
    ```

2.  **Download the Docker Compose file:**
    ```powershell
    Invoke-WebRequest -Uri "https://airflow.apache.org/docs/apache-airflow/stable/docker compose.yaml" -OutFile "docker compose.yaml"
    ```

3.  **Initialize the Airflow database:**
    ```powershell
    docker compose up airflow-init
    ```

4.  **Start Airflow:**
    ```powershell
    docker compose up
    ```

You can now access the Airflow UI at `http://localhost:8080` (login: `airflow`/`airflow`). Your DAGs from the `./dags` folder will be automatically loaded.
