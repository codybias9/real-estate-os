#!/bin/bash

# Real Estate OS - Complete Startup Script
# Starts all services and initializes the system

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

print_error() {
    echo -e "${RED}✗ ERROR: $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    print_success "Docker is running"
}

# Check if Docker Compose is available
check_docker_compose() {
    if ! command -v docker-compose &> /dev/null; then
        print_error "docker-compose not found. Please install Docker Compose."
        exit 1
    fi
    print_success "Docker Compose is available"
}

# Create .env file if it doesn't exist
setup_env() {
    if [ ! -f .env ]; then
        print_step "Creating .env file from .env.example..."
        cp .env.example .env
        print_success ".env file created"
        print_info "Please review and update .env file with your configuration"
    else
        print_info ".env file already exists"
    fi
}

# Start services
start_services() {
    print_step "Starting all services with Docker Compose..."

    # Check if user wants monitoring
    read -p "Do you want to start monitoring services (Prometheus/Grafana)? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose -f docker-compose-api.yaml --profile monitoring up -d
    else
        docker-compose -f docker-compose-api.yaml up -d
    fi

    print_success "Services started"
}

# Wait for services to be healthy
wait_for_services() {
    print_step "Waiting for services to be healthy..."

    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        echo -n "  Attempt $attempt/$max_attempts: "

        # Check database
        if docker-compose -f docker-compose-api.yaml exec -T postgres-api pg_isready -U postgres > /dev/null 2>&1; then
            echo -n "DB:✓ "
        else
            echo -n "DB:✗ "
        fi

        # Check Redis
        if docker-compose -f docker-compose-api.yaml exec -T redis-api redis-cli ping > /dev/null 2>&1; then
            echo -n "Redis:✓ "
        else
            echo -n "Redis:✗ "
        fi

        # Check API
        if curl -s http://localhost:8000/healthz > /dev/null 2>&1; then
            echo "API:✓"
            print_success "All services are healthy"
            return 0
        else
            echo "API:✗"
        fi

        attempt=$((attempt + 1))
        sleep 2
    done

    print_error "Services did not become healthy in time"
    return 1
}

# Run database migrations
run_migrations() {
    print_step "Running database migrations..."
    docker-compose -f docker-compose-api.yaml exec -T api alembic upgrade head || {
        print_info "Migrations not yet set up or already applied"
    }
}

# Seed database
seed_database() {
    read -p "Do you want to seed the database with sample data? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_step "Seeding database..."
        docker-compose -f docker-compose-api.yaml exec -T api python scripts/seed_data.py || {
            print_info "Seeding skipped or failed"
        }
    fi
}

# Show service URLs
show_urls() {
    print_header "Service URLs"
    echo -e "${GREEN}API Services:${NC}"
    echo "  • API:              http://localhost:8000"
    echo "  • API Docs:         http://localhost:8000/docs"
    echo "  • API ReDoc:        http://localhost:8000/redoc"
    echo "  • Health Check:     http://localhost:8000/health"
    echo ""
    echo -e "${GREEN}Infrastructure:${NC}"
    echo "  • PostgreSQL:       localhost:5432"
    echo "  • Redis:            localhost:6379"
    echo "  • RabbitMQ:         http://localhost:15672 (admin/admin)"
    echo "  • MinIO Console:    http://localhost:9001 (minioadmin/minioadmin)"
    echo "  • MailHog:          http://localhost:8025"
    echo ""

    if docker-compose -f docker-compose-api.yaml ps | grep -q prometheus; then
        echo -e "${GREEN}Monitoring:${NC}"
        echo "  • Prometheus:       http://localhost:9090"
        echo "  • Grafana:          http://localhost:3001 (admin/admin)"
        echo ""
    fi
}

# Show logs command
show_next_steps() {
    print_header "Next Steps"
    echo "1. View logs:"
    echo "   docker-compose -f docker-compose-api.yaml logs -f api"
    echo ""
    echo "2. Run the demo script:"
    echo "   ./demo_api.sh"
    echo ""
    echo "3. Create an admin user:"
    echo "   docker-compose -f docker-compose-api.yaml exec api python scripts/create_admin.py \\"
    echo "     admin@example.com Admin123! 'My Company'"
    echo ""
    echo "4. Stop services:"
    echo "   ./stop.sh"
    echo ""
}

# Main execution
main() {
    clear
    print_header "Real Estate OS - Startup Script"

    print_step "Checking prerequisites..."
    check_docker
    check_docker_compose

    setup_env

    start_services

    wait_for_services || {
        print_error "Failed to start services"
        print_info "Check logs with: docker-compose -f docker-compose-api.yaml logs"
        exit 1
    }

    run_migrations
    seed_database

    show_urls
    show_next_steps

    print_success "Real Estate OS is ready!"
}

# Run main function
main
