#!/bin/bash
# Rebuild API container with updated authentication code

echo "Stopping containers..."
docker compose -f docker-compose.api.yml down

echo "Rebuilding API container with no cache..."
docker compose -f docker-compose.api.yml build --no-cache api

echo "Starting containers..."
docker compose -f docker-compose.api.yml up -d

echo "Waiting for services to be healthy..."
sleep 10

echo "Checking API health..."
curl -f http://localhost:8000/healthz || echo "API not responding yet, give it a few more seconds"

echo ""
echo "Done! The API should now be running with updated authentication code."
echo "You can now test login at http://localhost:3000"
