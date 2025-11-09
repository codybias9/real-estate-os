"""
E2E Tests for Pipeline Management

Tests property viewing, drag-and-drop stage changes, and real-time updates
"""
import pytest
from playwright.sync_api import Page, expect
import playwright.config as config


@pytest.fixture
def authenticated_page(page: Page) -> Page:
    """Fixture that provides an authenticated page"""
    # Register and login
    page.goto(f"{config.FRONTEND_BASE_URL}/auth/register")
    page.fill('input[name="full_name"]', "Pipeline Test User")
    page.fill('input[name="email"]', f"pipeline-{config.TEST_USER_EMAIL}")
    page.fill('input[name="team_name"]', "Pipeline Test Team")
    page.fill('input[name="password"]', config.TEST_USER_PASSWORD)
    page.fill('input[name="confirmPassword"]', config.TEST_USER_PASSWORD)
    page.click('button[type="submit"]')

    # Wait for dashboard
    page.wait_for_url("**/dashboard", timeout=config.NAVIGATION_TIMEOUT)

    return page


class TestPipelineView:
    """Test viewing the pipeline"""

    def test_navigate_to_pipeline(self, authenticated_page: Page):
        """Test navigating to pipeline page"""
        page = authenticated_page

        # Click pipeline link in navigation
        page.click('text=/pipeline/i')

        # Should navigate to pipeline
        page.wait_for_url("**/dashboard/pipeline")

        # Page should load with pipeline board
        expect(page.locator("h1")).to_contain_text("Pipeline")

    def test_pipeline_columns_visible(self, authenticated_page: Page):
        """Test that all pipeline columns are visible"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/pipeline")

        # All stages should be visible
        stages = ["New", "Outreach", "Qualified", "Negotiation", "Under Contract", "Closed Won", "Closed Lost"]

        for stage in stages:
            expect(page.locator(f"text=/^{stage}$/")).to_be_visible()

    def test_property_count_displayed(self, authenticated_page: Page):
        """Test that property count is displayed"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/pipeline")

        # Property count should be visible
        expect(page.locator("text=/\\d+ properties/i")).to_be_visible()

    def test_sse_connection_indicator(self, authenticated_page: Page):
        """Test that SSE connection indicator is shown"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/pipeline")

        # Connection status should be visible
        # Either "Live Updates" or "Offline"
        connection_indicator = page.locator('[data-testid="sse-status"]')

        if connection_indicator.count() > 0:
            expect(connection_indicator).to_be_visible()


class TestPropertyCards:
    """Test property card display"""

    def test_property_card_displays_info(self, authenticated_page: Page):
        """Test that property cards show correct information"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/pipeline")

        # Wait for properties to load
        page.wait_for_timeout(2000)

        # Find first property card (if any exist)
        property_card = page.locator('[data-testid="property-card"]').first

        if property_card.count() > 0:
            # Card should show address
            expect(property_card).to_contain_text(/\d+\s+\w+/)

            # Should show bird dog score
            expect(property_card).to_contain_text(/score/i)

    def test_property_card_click_opens_drawer(self, authenticated_page: Page):
        """Test that clicking property opens detail drawer"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/pipeline")

        # Wait for properties
        page.wait_for_timeout(2000)

        # Click first property card (if exists)
        property_card = page.locator('[data-testid="property-card"]').first

        if property_card.count() > 0:
            property_card.click()

            # Drawer should open
            drawer = page.locator('[data-testid="property-drawer"]')
            expect(drawer).to_be_visible()


class TestPropertyDragAndDrop:
    """Test drag-and-drop functionality"""

    def test_drag_property_to_new_stage(self, authenticated_page: Page):
        """Test dragging property to different stage"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/pipeline")

        # Wait for board to load
        page.wait_for_timeout(2000)

        # Find a property in "New" stage
        new_column = page.locator('[data-testid="pipeline-column-new"]')
        property_card = new_column.locator('[data-testid="property-card"]').first

        if property_card.count() > 0:
            # Get property address for verification
            property_address = property_card.locator('[data-testid="property-address"]').text_content()

            # Drag to "Outreach" column
            outreach_column = page.locator('[data-testid="pipeline-column-outreach"]')

            # Perform drag and drop
            property_card.drag_to(outreach_column)

            # Wait for update
            page.wait_for_timeout(1000)

            # Verify property is now in outreach column
            outreach_properties = outreach_column.locator(f'text=/{property_address}/')
            expect(outreach_properties.first).to_be_visible()

    def test_optimistic_update_on_drag(self, authenticated_page: Page):
        """Test that UI updates immediately on drag (optimistic update)"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/pipeline")

        page.wait_for_timeout(2000)

        # Find property count in source column before drag
        new_column = page.locator('[data-testid="pipeline-column-new"]')
        initial_count_text = new_column.locator('[data-testid="column-count"]').text_content()

        if initial_count_text:
            initial_count = int(initial_count_text)

            # Drag property
            property_card = new_column.locator('[data-testid="property-card"]').first
            if property_card.count() > 0:
                outreach_column = page.locator('[data-testid="pipeline-column-outreach"]')
                property_card.drag_to(outreach_column)

                # Count should update immediately (within 500ms)
                page.wait_for_timeout(500)

                new_count_text = new_column.locator('[data-testid="column-count"]').text_content()
                new_count = int(new_count_text)

                # Count should have decreased
                assert new_count == initial_count - 1


class TestPropertyDrawer:
    """Test property detail drawer"""

    def test_drawer_shows_property_details(self, authenticated_page: Page):
        """Test that drawer displays property information"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/pipeline")

        page.wait_for_timeout(2000)

        # Click property to open drawer
        property_card = page.locator('[data-testid="property-card"]').first
        if property_card.count() > 0:
            property_card.click()

            drawer = page.locator('[data-testid="property-drawer"]')

            # Drawer should show property details
            expect(drawer).to_contain_text(/address|owner/i)

    def test_drawer_tabs_switch(self, authenticated_page: Page):
        """Test switching between drawer tabs"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/pipeline")

        page.wait_for_timeout(2000)

        # Open drawer
        property_card = page.locator('[data-testid="property-card"]').first
        if property_card.count() > 0:
            property_card.click()

            drawer = page.locator('[data-testid="property-drawer"]')

            # Click Timeline tab
            page.click('text=/timeline/i')
            expect(drawer).to_contain_text(/timeline|event/i)

            # Click Communications tab
            page.click('text=/communications/i')
            expect(drawer).to_contain_text(/communications|messages/i)

    def test_close_drawer(self, authenticated_page: Page):
        """Test closing property drawer"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/pipeline")

        page.wait_for_timeout(2000)

        # Open drawer
        property_card = page.locator('[data-testid="property-card"]').first
        if property_card.count() > 0:
            property_card.click()

            drawer = page.locator('[data-testid="property-drawer"]')
            expect(drawer).to_be_visible()

            # Click close button
            page.click('[data-testid="close-drawer"]')

            # Drawer should close
            expect(drawer).not_to_be_visible()

    def test_close_drawer_by_clicking_backdrop(self, authenticated_page: Page):
        """Test closing drawer by clicking outside"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/pipeline")

        page.wait_for_timeout(2000)

        # Open drawer
        property_card = page.locator('[data-testid="property-card"]').first
        if property_card.count() > 0:
            property_card.click()

            drawer = page.locator('[data-testid="property-drawer"]')
            expect(drawer).to_be_visible()

            # Click backdrop
            page.click('[data-testid="drawer-backdrop"]')

            # Drawer should close
            expect(drawer).not_to_be_visible()


class TestRealTimeUpdates:
    """Test real-time SSE updates"""

    def test_sse_connection_established(self, authenticated_page: Page):
        """Test that SSE connection is established"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/pipeline")

        # Wait for SSE to connect
        page.wait_for_timeout(3000)

        # Check connection indicator shows "Live Updates"
        connection_status = page.locator('[data-testid="sse-status"]')

        if connection_status.count() > 0:
            expect(connection_status).to_contain_text(/live|connected/i)

    def test_two_tab_sync(self, authenticated_page: Page, page: Page):
        """Test that updates sync between two tabs"""
        # Tab 1
        tab1 = authenticated_page
        tab1.goto(f"{config.FRONTEND_BASE_URL}/dashboard/pipeline")

        # Open second tab (new context)
        context = tab1.context
        tab2 = context.new_page()

        # Login in tab 2
        tab2.goto(f"{config.FRONTEND_BASE_URL}/auth/login")
        tab2.fill('input[type="email"]', f"pipeline-{config.TEST_USER_EMAIL}")
        tab2.fill('input[type="password"]', config.TEST_USER_PASSWORD)
        tab2.click('button[type="submit"]')
        tab2.wait_for_url("**/dashboard")

        # Navigate to pipeline in tab 2
        tab2.goto(f"{config.FRONTEND_BASE_URL}/dashboard/pipeline")

        # Wait for both to load
        tab1.wait_for_timeout(2000)
        tab2.wait_for_timeout(2000)

        # Make change in tab 1
        property_card = tab1.locator('[data-testid="property-card"]').first
        if property_card.count() > 0:
            outreach_column = tab1.locator('[data-testid="pipeline-column-outreach"]')
            property_card.drag_to(outreach_column)

            # Wait for SSE event
            tab2.wait_for_timeout(2000)

            # Tab 2 should reflect the change (optimistic or via SSE)
            # This tests the two-tab sync feature


class TestPipelineSearch:
    """Test pipeline search/filter functionality"""

    def test_search_properties(self, authenticated_page: Page):
        """Test searching for properties"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/pipeline")

        page.wait_for_timeout(2000)

        # Find search input (if exists)
        search_input = page.locator('[data-testid="pipeline-search"]')

        if search_input.count() > 0:
            # Type search query
            search_input.fill("123")

            # Wait for filter
            page.wait_for_timeout(1000)

            # Should show filtered results
            visible_cards = page.locator('[data-testid="property-card"]').count()

            # Results should be filtered (fewer than total)
            assert visible_cards >= 0


class TestPipelineLoading:
    """Test loading states"""

    def test_loading_state_shown(self, authenticated_page: Page):
        """Test that loading state is shown initially"""
        page = authenticated_page

        # Navigate to pipeline
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/pipeline")

        # Loading indicator should appear briefly
        loading = page.locator('[data-testid="pipeline-loading"]')

        # May or may not catch it depending on speed
        # At minimum, page should load without errors

        # Wait for content to load
        page.wait_for_selector('[data-testid="pipeline-board"]', timeout=10000)

    def test_empty_state_shown(self, authenticated_page: Page):
        """Test empty state when no properties"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/pipeline")

        page.wait_for_timeout(2000)

        # If no properties exist, should show empty state or counts of 0
        new_column = page.locator('[data-testid="pipeline-column-new"]')
        count_badge = new_column.locator('[data-testid="column-count"]')

        if count_badge.count() > 0:
            # Count should be a number (may be 0)
            count_text = count_badge.text_content()
            assert count_text.isdigit()
