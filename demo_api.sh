#!/bin/bash

# Real Estate OS API Demo Script
# This script demonstrates the complete workflow of the API

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# API Base URL
API_URL="${API_URL:-http://localhost:8000}"

# Global variables for storing IDs and tokens
ACCESS_TOKEN=""
USER_ID=""
ORG_ID=""
PROPERTY_ID=""
LEAD_ID=""
CAMPAIGN_ID=""
DEAL_ID=""

# Helper functions
print_header() {
    echo -e "\n${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║ $1${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}\n"
}

print_step() {
    echo -e "${GREEN}➤ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

make_request() {
    local method=$1
    local endpoint=$2
    local data=$3
    local description=$4

    print_step "$description"

    local headers=("Content-Type: application/json")
    if [ -n "$ACCESS_TOKEN" ]; then
        headers+=("Authorization: Bearer $ACCESS_TOKEN")
    fi

    local header_args=""
    for header in "${headers[@]}"; do
        header_args="$header_args -H \"$header\""
    done

    local cmd="curl -s -X $method"
    for header in "${headers[@]}"; do
        cmd="$cmd -H '$header'"
    done
    cmd="$cmd"

    if [ -n "$data" ]; then
        cmd="$cmd -d '$data'"
    fi

    cmd="$cmd '$API_URL$endpoint'"

    echo "$cmd" | sh
}

# Main demo flow
main() {
    clear
    echo -e "${BLUE}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║           Real Estate OS API - Interactive Demo                  ║
║                                                                   ║
║   A comprehensive demonstration of the Real Estate Operating      ║
║   System API capabilities including authentication, property     ║
║   management, lead tracking, campaigns, and deals.               ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}\n"

    print_info "API Base URL: $API_URL"
    print_info "Press Enter to begin the demo..."
    read

    # Step 1: Health Check
    print_header "Step 1: Health Check"
    response=$(make_request "GET" "/health" "" "Checking API health...")
    echo "$response" | jq '.'
    print_info "Press Enter to continue..."
    read

    # Step 2: Register User
    print_header "Step 2: User Registration"
    register_data='{
        "email": "demo@realestate.com",
        "password": "DemoPass123!",
        "first_name": "Demo",
        "last_name": "User",
        "organization_name": "Demo Real Estate Company"
    }'
    response=$(make_request "POST" "/api/v1/auth/register" "$register_data" "Registering new user...")
    echo "$response" | jq '.'

    ACCESS_TOKEN=$(echo "$response" | jq -r '.access_token')
    USER_ID=$(echo "$response" | jq -r '.user.id')
    ORG_ID=$(echo "$response" | jq -r '.user.organization_id')

    if [ "$ACCESS_TOKEN" != "null" ] && [ -n "$ACCESS_TOKEN" ]; then
        print_success "User registered successfully!"
        print_info "Access Token: ${ACCESS_TOKEN:0:30}..."
        print_info "User ID: $USER_ID"
        print_info "Organization ID: $ORG_ID"
    else
        print_error "Registration failed. User may already exist. Attempting login..."

        # Try to login instead
        login_data='{
            "email": "demo@realestate.com",
            "password": "DemoPass123!"
        }'
        response=$(make_request "POST" "/api/v1/auth/login" "$login_data" "Logging in...")
        echo "$response" | jq '.'

        ACCESS_TOKEN=$(echo "$response" | jq -r '.access_token')
        USER_ID=$(echo "$response" | jq -r '.user.id')
        ORG_ID=$(echo "$response" | jq -r '.user.organization_id')

        if [ "$ACCESS_TOKEN" != "null" ] && [ -n "$ACCESS_TOKEN" ]; then
            print_success "Logged in successfully!"
        else
            print_error "Login failed. Exiting demo."
            exit 1
        fi
    fi

    print_info "Press Enter to continue..."
    read

    # Step 3: Get Current User
    print_header "Step 3: Get Current User Profile"
    response=$(make_request "GET" "/api/v1/auth/me" "" "Fetching user profile...")
    echo "$response" | jq '.'
    print_info "Press Enter to continue..."
    read

    # Step 4: Create Property
    print_header "Step 4: Create Property"
    property_data='{
        "address": "123 Sunset Boulevard",
        "city": "Los Angeles",
        "state": "CA",
        "zip_code": "90028",
        "country": "USA",
        "property_type": "single_family",
        "status": "available",
        "price": 850000,
        "bedrooms": 4,
        "bathrooms": 3.5,
        "square_feet": 2800,
        "lot_size": 6500,
        "year_built": 2018,
        "description": "Beautiful modern home in prime location with panoramic views"
    }'
    response=$(make_request "POST" "/api/v1/properties" "$property_data" "Creating property...")
    echo "$response" | jq '.'

    PROPERTY_ID=$(echo "$response" | jq -r '.id')
    print_success "Property created with ID: $PROPERTY_ID"
    print_info "Press Enter to continue..."
    read

    # Step 5: List Properties
    print_header "Step 5: List All Properties"
    response=$(make_request "GET" "/api/v1/properties?limit=10" "" "Fetching properties...")
    echo "$response" | jq '.'
    print_info "Press Enter to continue..."
    read

    # Step 6: Create Lead
    print_header "Step 6: Create Lead"
    lead_data='{
        "first_name": "John",
        "last_name": "Buyer",
        "email": "john.buyer@example.com",
        "phone": "+1-555-0123",
        "source": "website",
        "status": "new",
        "budget": 900000,
        "timeline": "0-3 months",
        "notes": "Interested in properties in West LA area"
    }'
    response=$(make_request "POST" "/api/v1/leads" "$lead_data" "Creating lead...")
    echo "$response" | jq '.'

    LEAD_ID=$(echo "$response" | jq -r '.id')
    print_success "Lead created with ID: $LEAD_ID"
    print_info "Press Enter to continue..."
    read

    # Step 7: Add Lead Activity
    print_header "Step 7: Add Lead Activity"
    activity_data='{
        "activity_type": "call",
        "subject": "Initial consultation call",
        "description": "Discussed budget and property preferences. Very interested in modern homes.",
        "outcome": "success"
    }'
    response=$(make_request "POST" "/api/v1/leads/$LEAD_ID/activities" "$activity_data" "Adding lead activity...")
    echo "$response" | jq '.'
    print_info "Press Enter to continue..."
    read

    # Step 8: Create Deal
    print_header "Step 8: Create Deal"
    deal_data='{
        "property_id": '"$PROPERTY_ID"',
        "lead_id": '"$LEAD_ID"',
        "deal_type": "sale",
        "stage": "proposal",
        "value": 850000,
        "commission_rate": 5.0,
        "probability": 70,
        "notes": "Buyer is pre-qualified and very interested"
    }'
    response=$(make_request "POST" "/api/v1/deals" "$deal_data" "Creating deal...")
    echo "$response" | jq '.'

    DEAL_ID=$(echo "$response" | jq -r '.id')
    print_success "Deal created with ID: $DEAL_ID"
    print_info "Press Enter to continue..."
    read

    # Step 9: Update Deal Stage
    print_header "Step 9: Update Deal Stage"
    update_data='{
        "stage": "negotiation",
        "probability": 85,
        "notes": "Received initial offer, negotiating terms"
    }'
    response=$(make_request "PUT" "/api/v1/deals/$DEAL_ID" "$update_data" "Updating deal stage...")
    echo "$response" | jq '.'
    print_info "Press Enter to continue..."
    read

    # Step 10: Get Analytics Dashboard
    print_header "Step 10: Analytics Dashboard"
    response=$(make_request "GET" "/api/v1/analytics/dashboard" "" "Fetching dashboard metrics...")
    echo "$response" | jq '.'
    print_info "Press Enter to continue..."
    read

    # Step 11: Create Campaign
    print_header "Step 11: Create Email Campaign"
    campaign_data='{
        "name": "New Property Alert - Sunset Blvd",
        "campaign_type": "email",
        "subject": "New Listing: Stunning 4BR Home in LA",
        "content": "Check out our latest listing at 123 Sunset Boulevard!",
        "status": "draft"
    }'
    response=$(make_request "POST" "/api/v1/campaigns" "$campaign_data" "Creating campaign...")
    echo "$response" | jq '.'

    CAMPAIGN_ID=$(echo "$response" | jq -r '.id')
    print_success "Campaign created with ID: $CAMPAIGN_ID"
    print_info "Press Enter to continue..."
    read

    # Final Summary
    print_header "Demo Complete!"
    echo -e "${GREEN}Successfully demonstrated:${NC}"
    echo "  ✓ User registration and authentication"
    echo "  ✓ Property management"
    echo "  ✓ Lead tracking and activities"
    echo "  ✓ Deal pipeline management"
    echo "  ✓ Analytics dashboard"
    echo "  ✓ Campaign creation"
    echo ""
    print_info "Created Resources:"
    echo "  • User ID: $USER_ID"
    echo "  • Organization ID: $ORG_ID"
    echo "  • Property ID: $PROPERTY_ID"
    echo "  • Lead ID: $LEAD_ID"
    echo "  • Deal ID: $DEAL_ID"
    echo "  • Campaign ID: $CAMPAIGN_ID"
    echo ""
    print_info "Access Token (for API exploration): ${ACCESS_TOKEN:0:50}..."
    echo ""
    print_info "Next Steps:"
    echo "  1. Explore the API documentation at $API_URL/docs"
    echo "  2. Try the real-time updates at $API_URL/api/v1/sse/stream"
    echo "  3. Check health status at $API_URL/health"
    echo ""
    print_success "Thank you for exploring Real Estate OS API!"
    echo ""
}

# Run the demo
main
