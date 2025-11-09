#!/bin/bash
# Script to run Alembic migrations inside the Docker container
#
# Usage from host machine:
#   docker exec -it real-estate-os-api-1 bash /app/run_migrations.sh
#
# Or copy and run directly inside the container:
#   docker exec -it real-estate-os-api-1 bash
#   ./run_migrations.sh

set -e

echo "================================"
echo "Running Alembic Migrations"
echo "================================"
echo ""

# Change to the db directory where alembic.ini is located
cd /app/db

# Display current database connection
echo "Database: ${DB_DSN}"
echo ""

# Run migrations
echo "Running: alembic upgrade head"
alembic upgrade head

echo ""
echo "================================"
echo "Migrations completed successfully!"
echo "================================"
