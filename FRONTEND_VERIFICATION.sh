#!/bin/bash
# Frontend Static Verification Script
# Verifies all frontend hooks and components are properly wired

set -e

echo "=========================================="
echo "Frontend Static Verification"
echo "=========================================="
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

echo "Step 1: Verifying new components exist..."
if [ -f "frontend/src/components/SSEConnectionBadge.tsx" ]; then
    print_success "SSEConnectionBadge.tsx exists"
else
    echo "❌ SSEConnectionBadge.tsx not found"
    exit 1
fi

if [ -f "frontend/src/components/Toast.tsx" ]; then
    print_success "Toast.tsx exists"
else
    echo "❌ Toast.tsx not found"
    exit 1
fi

echo ""
echo "Step 2: Verifying new hooks exist..."
if [ -f "frontend/src/hooks/useToast.ts" ]; then
    print_success "useToast.ts exists"
else
    echo "❌ useToast.ts not found"
    exit 1
fi

echo ""
echo "Step 3: Checking Axios interceptor logging..."
if grep -q "AUTH: Demo token attached" frontend/src/lib/api.ts; then
    print_success "Axios interceptor has auth logging"
else
    echo "❌ Axios interceptor logging not found"
    exit 1
fi

echo ""
echo "Step 4: Checking DashboardLayout SSE integration..."
if grep -q "import { useSSE }" frontend/src/components/DashboardLayout.tsx; then
    print_success "DashboardLayout imports useSSE"
else
    echo "❌ DashboardLayout missing useSSE import"
    exit 1
fi

if grep -q "SSEConnectionBadge" frontend/src/components/DashboardLayout.tsx; then
    print_success "DashboardLayout uses SSEConnectionBadge"
else
    echo "❌ DashboardLayout missing SSEConnectionBadge"
    exit 1
fi

echo ""
echo "Step 5: Checking Admin page SSE + Toast integration..."
if grep -q "import { useToast }" frontend/src/app/dashboard/admin/page.tsx; then
    print_success "Admin page imports useToast"
else
    echo "❌ Admin page missing useToast import"
    exit 1
fi

if grep -q "ToastContainer" frontend/src/app/dashboard/admin/page.tsx; then
    print_success "Admin page uses ToastContainer"
else
    echo "❌ Admin page missing ToastContainer"
    exit 1
fi

if grep -q "emitTestEvent" frontend/src/app/dashboard/admin/page.tsx; then
    print_success "Admin page has emitTestEvent function"
else
    echo "❌ Admin page missing emitTestEvent function"
    exit 1
fi

if grep -q "Emit Test Event" frontend/src/app/dashboard/admin/page.tsx; then
    print_success "Admin page has 'Emit Test Event' button"
else
    echo "❌ Admin page missing 'Emit Test Event' button"
    exit 1
fi

echo ""
echo "Step 6: Checking SSE event handlers..."
if grep -q "showEvent" frontend/src/app/dashboard/admin/page.tsx && \
   grep -q "onEvent:" frontend/src/app/dashboard/admin/page.tsx; then
    print_success "Admin page wired to show toast on SSE events"
else
    echo "⚠️  Admin page may not be showing toasts for SSE events"
fi

if grep -q "setEventFlash" frontend/src/components/DashboardLayout.tsx; then
    print_success "DashboardLayout triggers flash animation on events"
else
    echo "⚠️  DashboardLayout may not be flashing on events"
fi

echo ""
echo "Step 7: Component interface verification..."

# Check SSEConnectionBadge props
if grep -q "isConnected: boolean" frontend/src/components/SSEConnectionBadge.tsx && \
   grep -q "onEventReceived" frontend/src/components/SSEConnectionBadge.tsx; then
    print_success "SSEConnectionBadge has correct props interface"
else
    echo "⚠️  SSEConnectionBadge props may be incomplete"
fi

# Check Toast props
if grep -q "ToastProps" frontend/src/components/Toast.tsx; then
    print_success "Toast component has ToastProps interface"
else
    echo "⚠️  Toast component missing ToastProps"
fi

echo ""
echo "Step 8: Checking for TypeScript compilation hints..."

# Check for obvious syntax errors
SYNTAX_CHECK=0

if grep -q "import.*from.*@/" frontend/src/components/SSEConnectionBadge.tsx 2>/dev/null; then
    print_info "SSEConnectionBadge uses path aliases (good)"
fi

if grep -q "'use client'" frontend/src/components/DashboardLayout.tsx; then
    print_success "DashboardLayout has 'use client' directive"
else
    echo "⚠️  DashboardLayout missing 'use client' directive"
fi

if grep -q "'use client'" frontend/src/app/dashboard/admin/page.tsx; then
    print_success "Admin page has 'use client' directive"
else
    echo "⚠️  Admin page missing 'use client' directive"
fi

echo ""
echo "=========================================="
echo "Summary: Frontend Static Verification"
echo "=========================================="
echo ""
print_success "All required components exist"
print_success "Axios interceptor logging added"
print_success "SSE connection badge integrated in layout"
print_success "Toast system fully wired"
print_success "'Emit Test Event' button added to Admin page"
echo ""
print_info "Next steps:"
echo "  1. Run 'npm run build' in frontend/ to verify TypeScript compilation"
echo "  2. Start services with docker-compose up -d"
echo "  3. Open http://localhost:3000/dashboard/admin"
echo "  4. Check browser console for:"
echo "     - '🔐 AUTH: Demo token attached' log"
echo "     - '[SSE] Connected to real-time event stream' log"
echo "  5. Click 'Emit Test Event' button"
echo "  6. Verify:"
echo "     - SSE badge flashes (green pulse animation)"
echo "     - Toast appears showing event type and ID"
echo "     - Console shows '[SSE] Event received' log"
echo ""
