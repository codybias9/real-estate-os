#!/bin/bash

# Real Estate OS - Stop Script
# Stops all running services

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}\n"
}

print_step() {
    echo -e "${GREEN}▶ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

main() {
    print_header "Real Estate OS - Stopping Services"

    print_step "Stopping all services..."
    docker-compose -f docker-compose-api.yaml --profile monitoring down

    print_success "All services stopped"

    echo ""
    print_info "Data volumes are preserved. To remove them, run:"
    echo "  docker-compose -f docker-compose-api.yaml down -v"
    echo ""
    print_info "To start again, run: ./start.sh"
}

main
