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

# Stay in /app directory so Python can find modules
cd /app

# Display current database connection
echo "Database: ${DB_DSN}"
echo ""

# Run migrations with config file in db/ directory
echo "Running: alembic -c db/alembic.ini upgrade head"
alembic -c db/alembic.ini upgrade head

echo ""
echo "================================"
echo "Migrations completed successfully!"
echo "================================"
