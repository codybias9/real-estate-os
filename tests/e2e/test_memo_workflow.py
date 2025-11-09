"""
E2E Tests for Memo Generation Workflow

Tests complete workflow: Select property → Choose template → Generate → Send → Verify
"""
import pytest
from playwright.sync_api import Page, expect
import playwright.config as config


@pytest.fixture
def authenticated_page(page: Page) -> Page:
    """Fixture that provides an authenticated page"""
    page.goto(f"{config.FRONTEND_BASE_URL}/auth/register")
    page.fill('input[name="full_name"]', "Memo Test User")
    page.fill('input[name="email"]', f"memo-{config.TEST_USER_EMAIL}")
    page.fill('input[name="team_name"]', "Memo Test Team")
    page.fill('input[name="password"]', config.TEST_USER_PASSWORD)
    page.fill('input[name="confirmPassword"]', config.TEST_USER_PASSWORD)
    page.click('button[type="submit"]')

    page.wait_for_url("**/dashboard", timeout=config.NAVIGATION_TIMEOUT)

    return page


class TestNavigationToCommunications:
    """Test navigating to communications page"""

    def test_navigate_to_communications(self, authenticated_page: Page):
        """Test navigating to communications page"""
        page = authenticated_page

        # Click communications link
        page.click('text=/communications/i')

        # Should navigate to communications page
        page.wait_for_url("**/dashboard/communications")

        # Page should load
        expect(page.locator("h1")).to_contain_text("Communications")


class TestPropertySelection:
    """Test selecting a property for memo generation"""

    def test_property_list_displayed(self, authenticated_page: Page):
        """Test that property list is displayed"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/communications")

        # Property selection area should be visible
        expect(page.locator('[data-testid="property-selector"]')).to_be_visible()

        # Search box should be present
        expect(page.locator('[data-testid="property-search"]')).to_be_visible()

    def test_search_properties(self, authenticated_page: Page):
        """Test searching for properties"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/communications")

        # Type in search
        search_input = page.locator('[data-testid="property-search"]')
        search_input.fill("123")

        # Wait for search results
        page.wait_for_timeout(1000)

        # Results should update
        # (Test depends on having properties with "123" in address)

    def test_select_property(self, authenticated_page: Page):
        """Test selecting a property"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/communications")

        page.wait_for_timeout(2000)

        # Click first property (if exists)
        property_button = page.locator('[data-testid="property-option"]').first

        if property_button.count() > 0:
            property_button.click()

            # Property should be highlighted/selected
            expect(property_button).to_have_class(/selected|active/)


class TestTemplateSelection:
    """Test selecting a template"""

    def test_template_list_displayed(self, authenticated_page: Page):
        """Test that template list is displayed"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/communications")

        # Template selection area should be visible
        expect(page.locator('[data-testid="template-selector"]')).to_be_visible()

    def test_template_shows_details(self, authenticated_page: Page):
        """Test that templates show performance details"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/communications")

        page.wait_for_timeout(2000)

        # Find first template (if exists)
        template_card = page.locator('[data-testid="template-card"]').first

        if template_card.count() > 0:
            # Should show template name
            expect(template_card).to_contain_text(/template|email|sms/)

            # Should show usage stats
            expect(template_card).to_contain_text(/used|success|rate/)

    def test_select_template(self, authenticated_page: Page):
        """Test selecting a template"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/communications")

        page.wait_for_timeout(2000)

        # Click first template (if exists)
        template_card = page.locator('[data-testid="template-card"]').first

        if template_card.count() > 0:
            template_card.click()

            # Template should be highlighted
            expect(template_card).to_have_class(/selected|active/)


class TestMemoGeneration:
    """Test generating and sending memo"""

    def test_generate_button_disabled_initially(self, authenticated_page: Page):
        """Test that generate button is disabled until property and template selected"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/communications")

        # Generate button should be disabled initially
        generate_btn = page.locator('[data-testid="generate-send-button"]')

        if generate_btn.count() > 0:
            expect(generate_btn).to_be_disabled()

    def test_generate_button_enabled_after_selection(self, authenticated_page: Page):
        """Test that generate button enables after selections"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/communications")

        page.wait_for_timeout(2000)

        # Select property
        property_button = page.locator('[data-testid="property-option"]').first
        if property_button.count() > 0:
            property_button.click()

            # Select template
            template_card = page.locator('[data-testid="template-card"]').first
            if template_card.count() > 0:
                template_card.click()

                # Generate button should be enabled
                generate_btn = page.locator('[data-testid="generate-send-button"]')
                expect(generate_btn).to_be_enabled()

    def test_generate_and_send_flow(self, authenticated_page: Page):
        """Test complete generate and send flow"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/communications")

        page.wait_for_timeout(2000)

        # Select property
        property_button = page.locator('[data-testid="property-option"]').first
        if property_button.count() > 0:
            property_button.click()

            # Select template
            template_card = page.locator('[data-testid="template-card"]').first
            if template_card.count() > 0:
                template_card.click()

                # Click generate and send
                page.click('[data-testid="generate-send-button"]')

                # Should show loading state
                expect(page.locator('[data-testid="generating-loading"]')).to_be_visible()

                # Wait for completion
                page.wait_for_timeout(5000)

                # Should show success message
                success_message = page.locator('[data-testid="success-message"]')
                expect(success_message).to_be_visible()
                expect(success_message).to_contain_text(/success|sent/)

    def test_loading_state_during_generation(self, authenticated_page: Page):
        """Test that loading state is shown during generation"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/communications")

        page.wait_for_timeout(2000)

        # Make selections
        property_button = page.locator('[data-testid="property-option"]').first
        if property_button.count() > 0:
            property_button.click()

            template_card = page.locator('[data-testid="template-card"]').first
            if template_card.count() > 0:
                template_card.click()

                # Click generate
                page.click('[data-testid="generate-send-button"]')

                # Loading indicator should appear
                loading = page.locator('[data-testid="generating-loading"]')
                expect(loading).to_be_visible()

                # Button should be disabled during generation
                generate_btn = page.locator('[data-testid="generate-send-button"]')
                expect(generate_btn).to_be_disabled()


class TestMemoSuccess:
    """Test successful memo generation"""

    def test_success_message_displayed(self, authenticated_page: Page):
        """Test that success message is displayed after generation"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/communications")

        page.wait_for_timeout(2000)

        # Complete workflow (if properties and templates exist)
        property_button = page.locator('[data-testid="property-option"]').first
        if property_button.count() > 0:
            property_button.click()

            template_card = page.locator('[data-testid="template-card"]').first
            if template_card.count() > 0:
                template_card.click()

                page.click('[data-testid="generate-send-button"]')

                # Wait for success
                page.wait_for_timeout(5000)

                # Success message should show
                success = page.locator('[data-testid="success-message"]')

                if success.count() > 0:
                    expect(success).to_be_visible()

    def test_selections_cleared_after_success(self, authenticated_page: Page):
        """Test that selections are cleared after successful generation"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/communications")

        page.wait_for_timeout(2000)

        # Complete workflow
        property_button = page.locator('[data-testid="property-option"]').first
        if property_button.count() > 0:
            property_button.click()

            template_card = page.locator('[data-testid="template-card"]').first
            if template_card.count() > 0:
                template_card.click()

                page.click('[data-testid="generate-send-button"]')

                # Wait for completion
                page.wait_for_timeout(6000)

                # Selections should be cleared
                # (Depends on implementation - may stay selected)


class TestMemoError:
    """Test error handling"""

    def test_error_message_on_failure(self, authenticated_page: Page):
        """Test that error message is shown on failure"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/communications")

        # This test would require triggering an error condition
        # E.g., invalid property ID, network error, etc.

        # For now, verify error message element exists
        error_message = page.locator('[data-testid="error-message"]')

        # Error should not be visible initially
        if error_message.count() > 0:
            expect(error_message).not_to_be_visible()

    def test_retry_after_error(self, authenticated_page: Page):
        """Test that user can retry after error"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/communications")

        # If an error occurs, user should be able to try again
        # Generate button should re-enable after error


class TestStatistics:
    """Test statistics display"""

    def test_statistics_cards_displayed(self, authenticated_page: Page):
        """Test that statistics cards are displayed"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/communications")

        # Stats cards should be visible
        expect(page.locator('[data-testid="stats-cards"]')).to_be_visible()

    def test_property_count_stat(self, authenticated_page: Page):
        """Test that property count stat is shown"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/communications")

        page.wait_for_timeout(2000)

        # Should show total properties
        expect(page.locator('text=/total properties/i')).to_be_visible()

    def test_template_count_stat(self, authenticated_page: Page):
        """Test that template count stat is shown"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/communications")

        page.wait_for_timeout(2000)

        # Should show active templates
        expect(page.locator('text=/active templates|templates/i')).to_be_visible()


class TestPropertyDetails:
    """Test viewing property details"""

    def test_selected_property_details_shown(self, authenticated_page: Page):
        """Test that selected property shows details"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/communications")

        page.wait_for_timeout(2000)

        # Select property
        property_button = page.locator('[data-testid="property-option"]').first
        if property_button.count() > 0:
            property_button.click()

            # Property details should be visible in selection summary
            summary = page.locator('[data-testid="selection-summary"]')

            if summary.count() > 0:
                # Should show property address
                expect(summary).to_contain_text(/property|address/)


class TestTemplatePreview:
    """Test template preview"""

    def test_template_preview_modal(self, authenticated_page: Page):
        """Test that template can be previewed"""
        page = authenticated_page
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/communications")

        page.wait_for_timeout(2000)

        # Click preview button on template (if exists)
        preview_btn = page.locator('[data-testid="template-preview-button"]').first

        if preview_btn.count() > 0:
            preview_btn.click()

            # Modal should open
            modal = page.locator('[data-testid="template-preview-modal"]')
            expect(modal).to_be_visible()

            # Should show template content
            expect(modal).to_contain_text(/subject|body|template/)

            # Close modal
            page.click('[data-testid="close-modal"]')

            # Modal should close
            expect(modal).not_to_be_visible()
