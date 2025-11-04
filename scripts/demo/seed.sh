#!/bin/bash
# =============================================================================
# Seed Demo Data
# Populates database with realistic demo data
# =============================================================================
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Real Estate OS - Demo Data Seeding${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if API is running
echo -e "${YELLOW}🔍 Checking if API is accessible...${NC}"
if ! curl -sf http://localhost:8000/healthz > /dev/null 2>&1; then
    echo -e "${RED}❌ API not accessible at http://localhost:8000${NC}"
    echo -e "${YELLOW}   Please start the Docker stack first:${NC}"
    echo -e "${YELLOW}   ./scripts/docker/start.sh${NC}"
    exit 1
fi
echo -e "${GREEN}✓ API is accessible${NC}"
echo ""

# Run seed script
echo -e "${YELLOW}🌱 Seeding database with demo data...${NC}"
echo ""

# Execute seed script inside API container
docker-compose exec -T api python scripts/seed_data.py

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Demo data seeded successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

echo -e "${BLUE}📋 Demo Credentials:${NC}"
echo ""
echo -e "  ${YELLOW}Admin:${NC}   admin@demo.com   / password123"
echo -e "  ${YELLOW}Manager:${NC} manager@demo.com / password123"
echo -e "  ${YELLOW}Agent:${NC}   agent@demo.com   / password123"
echo -e "  ${YELLOW}Viewer:${NC}  viewer@demo.com  / password123"
echo ""

echo -e "${BLUE}💡 Next Steps:${NC}"
echo ""
echo -e "  1. Open API docs:    ${YELLOW}http://localhost:8000/docs${NC}"
echo -e "  2. Login with admin: ${YELLOW}POST /api/v1/auth/login${NC}"
echo -e "  3. Explore data:     ${YELLOW}GET /api/v1/properties${NC}"
echo -e "  4. Run demo:         ${YELLOW}cat docs/DEMO_GUIDE.md${NC}"
echo ""
