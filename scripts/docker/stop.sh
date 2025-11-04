#!/bin/bash
# =============================================================================
# Stop Real Estate OS Docker Stack
# =============================================================================
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Real Estate OS - Docker Stack Shutdown${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Parse command line arguments
REMOVE_VOLUMES=false
if [ "$1" == "--volumes" ] || [ "$1" == "-v" ]; then
    REMOVE_VOLUMES=true
    echo -e "${YELLOW}⚠️  Warning: Will remove all volumes (data will be lost!)${NC}"
    echo ""
fi

# Stop all services
echo -e "${YELLOW}🛑 Stopping all services...${NC}"
docker-compose down

if [ "$REMOVE_VOLUMES" == true ]; then
    echo -e "${YELLOW}🗑️  Removing volumes...${NC}"
    docker-compose down -v
    echo -e "${RED}✓ All data removed${NC}"
else
    echo -e "${GREEN}✓ Services stopped (data preserved)${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Stack stopped successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

if [ "$REMOVE_VOLUMES" == false ]; then
    echo -e "${BLUE}💡 Tips:${NC}"
    echo ""
    echo -e "  ${YELLOW}Restart stack:${NC}    ./scripts/docker/start.sh"
    echo -e "  ${YELLOW}Remove data:${NC}      ./scripts/docker/stop.sh --volumes"
    echo -e "  ${YELLOW}View containers:${NC}  docker ps -a"
    echo ""
fi
