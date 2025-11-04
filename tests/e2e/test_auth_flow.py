"""
E2E Tests for Authentication Flows

Tests user registration, login, and logout flows from browser perspective
"""
import pytest
from playwright.sync_api import Page, expect
import playwright.config as config


class TestUserRegistration:
    """Test user registration flow"""

    def test_successful_registration(self, page: Page):
        """Test complete registration flow"""
        # Navigate to registration page
        page.goto(f"{config.FRONTEND_BASE_URL}/auth/register")

        # Verify registration form is visible
        expect(page.locator("h1")).to_contain_text("Register")

        # Fill in registration form
        page.fill('input[name="full_name"]', config.TEST_USER_NAME)
        page.fill('input[name="email"]', f"new-{config.TEST_USER_EMAIL}")
        page.fill('input[name="team_name"]', config.TEST_TEAM_NAME)
        page.fill('input[name="password"]', config.TEST_USER_PASSWORD)
        page.fill('input[name="confirmPassword"]', config.TEST_USER_PASSWORD)

        # Submit form
        page.click('button[type="submit"]')

        # Should redirect to dashboard or login
        page.wait_for_url("**/dashboard", timeout=config.NAVIGATION_TIMEOUT)

        # Verify dashboard loaded
        expect(page.locator("h1")).to_contain_text("Dashboard")

    def test_registration_validation_errors(self, page: Page):
        """Test form validation on registration"""
        page.goto(f"{config.FRONTEND_BASE_URL}/auth/register")

        # Try to submit empty form
        page.click('button[type="submit"]')

        # Should show validation errors
        expect(page.locator("text=/required/i")).to_be_visible()

    def test_password_mismatch_error(self, page: Page):
        """Test password confirmation mismatch"""
        page.goto(f"{config.FRONTEND_BASE_URL}/auth/register")

        # Fill form with mismatched passwords
        page.fill('input[name="full_name"]', "Test User")
        page.fill('input[name="email"]', "test@example.com")
        page.fill('input[name="team_name"]', "Test Team")
        page.fill('input[name="password"]', "Password123!")
        page.fill('input[name="confirmPassword"]', "DifferentPassword123!")

        page.click('button[type="submit"]')

        # Should show mismatch error
        expect(page.locator("text=/passwords.*match/i")).to_be_visible()

    def test_duplicate_email_error(self, page: Page):
        """Test registration with existing email"""
        # First registration
        page.goto(f"{config.FRONTEND_BASE_URL}/auth/register")

        email = f"duplicate-{config.TEST_USER_EMAIL}"
        page.fill('input[name="full_name"]', "First User")
        page.fill('input[name="email"]', email)
        page.fill('input[name="team_name"]', "First Team")
        page.fill('input[name="password"]', config.TEST_USER_PASSWORD)
        page.fill('input[name="confirmPassword"]', config.TEST_USER_PASSWORD)
        page.click('button[type="submit"]')

        # Wait for success
        page.wait_for_url("**/dashboard", timeout=config.NAVIGATION_TIMEOUT)

        # Logout
        page.click('[data-testid="user-menu"]')
        page.click('text=/logout/i')

        # Try to register again with same email
        page.goto(f"{config.FRONTEND_BASE_URL}/auth/register")
        page.fill('input[name="full_name"]', "Second User")
        page.fill('input[name="email"]', email)
        page.fill('input[name="team_name"]', "Second Team")
        page.fill('input[name="password"]', config.TEST_USER_PASSWORD)
        page.fill('input[name="confirmPassword"]', config.TEST_USER_PASSWORD)
        page.click('button[type="submit"]')

        # Should show duplicate email error
        expect(page.locator("text=/already.*exists|email.*taken/i")).to_be_visible()


class TestUserLogin:
    """Test user login flow"""

    @pytest.fixture(autouse=True)
    def setup_user(self, page: Page):
        """Create a user before each login test"""
        # Register user
        page.goto(f"{config.FRONTEND_BASE_URL}/auth/register")
        page.fill('input[name="full_name"]', config.TEST_USER_NAME)
        page.fill('input[name="email"]', config.TEST_USER_EMAIL)
        page.fill('input[name="team_name"]', config.TEST_TEAM_NAME)
        page.fill('input[name="password"]', config.TEST_USER_PASSWORD)
        page.fill('input[name="confirmPassword"]', config.TEST_USER_PASSWORD)
        page.click('button[type="submit"]')

        # Wait for registration
        page.wait_for_url("**/dashboard", timeout=config.NAVIGATION_TIMEOUT)

        # Logout
        page.click('[data-testid="user-menu"]')
        page.click('text=/logout/i')

        # Wait for redirect to login
        page.wait_for_url("**/auth/login")

    def test_successful_login(self, page: Page):
        """Test successful login flow"""
        page.goto(f"{config.FRONTEND_BASE_URL}/auth/login")

        # Fill login form
        page.fill('input[type="email"]', config.TEST_USER_EMAIL)
        page.fill('input[type="password"]', config.TEST_USER_PASSWORD)

        # Submit
        page.click('button[type="submit"]')

        # Should redirect to dashboard
        page.wait_for_url("**/dashboard", timeout=config.NAVIGATION_TIMEOUT)

        # Verify user is logged in
        expect(page.locator("text=/welcome|dashboard/i")).to_be_visible()

        # User menu should show user name
        expect(page.locator('[data-testid="user-menu"]')).to_contain_text(config.TEST_USER_NAME)

    def test_invalid_password(self, page: Page):
        """Test login with wrong password"""
        page.goto(f"{config.FRONTEND_BASE_URL}/auth/login")

        page.fill('input[type="email"]', config.TEST_USER_EMAIL)
        page.fill('input[type="password"]', "WrongPassword123!")

        page.click('button[type="submit"]')

        # Should show error message
        expect(page.locator("text=/invalid.*credentials|incorrect.*password/i")).to_be_visible()

        # Should stay on login page
        expect(page).to_have_url(f"{config.FRONTEND_BASE_URL}/auth/login")

    def test_nonexistent_user(self, page: Page):
        """Test login with non-existent email"""
        page.goto(f"{config.FRONTEND_BASE_URL}/auth/login")

        page.fill('input[type="email"]', "nonexistent@example.com")
        page.fill('input[type="password"]', "SomePassword123!")

        page.click('button[type="submit"]')

        # Should show error
        expect(page.locator("text=/invalid.*credentials|user.*not.*found/i")).to_be_visible()

    def test_login_validation(self, page: Page):
        """Test login form validation"""
        page.goto(f"{config.FRONTEND_BASE_URL}/auth/login")

        # Try empty submission
        page.click('button[type="submit"]')

        # Should show validation errors
        expect(page.locator("text=/required/i")).to_be_visible()

    def test_remember_me(self, page: Page):
        """Test remember me functionality"""
        page.goto(f"{config.FRONTEND_BASE_URL}/auth/login")

        page.fill('input[type="email"]', config.TEST_USER_EMAIL)
        page.fill('input[type="password"]', config.TEST_USER_PASSWORD)

        # Check remember me (if it exists)
        remember_checkbox = page.locator('input[type="checkbox"][name="remember"]')
        if remember_checkbox.count() > 0:
            remember_checkbox.check()

        page.click('button[type="submit"]')

        # Should login successfully
        page.wait_for_url("**/dashboard", timeout=config.NAVIGATION_TIMEOUT)


class TestUserLogout:
    """Test user logout flow"""

    @pytest.fixture(autouse=True)
    def login_user(self, page: Page):
        """Login before each logout test"""
        # Register and login
        page.goto(f"{config.FRONTEND_BASE_URL}/auth/register")
        page.fill('input[name="full_name"]', config.TEST_USER_NAME)
        page.fill('input[name="email"]', f"logout-{config.TEST_USER_EMAIL}")
        page.fill('input[name="team_name"]', config.TEST_TEAM_NAME)
        page.fill('input[name="password"]', config.TEST_USER_PASSWORD)
        page.fill('input[name="confirmPassword"]', config.TEST_USER_PASSWORD)
        page.click('button[type="submit"]')

        page.wait_for_url("**/dashboard", timeout=config.NAVIGATION_TIMEOUT)

    def test_successful_logout(self, page: Page):
        """Test logout flow"""
        # Click user menu
        page.click('[data-testid="user-menu"]')

        # Click logout
        page.click('text=/logout/i')

        # Should redirect to login page
        page.wait_for_url("**/auth/login", timeout=config.NAVIGATION_TIMEOUT)

        # Verify logged out (no user menu)
        expect(page.locator('[data-testid="user-menu"]')).not_to_be_visible()

    def test_protected_route_after_logout(self, page: Page):
        """Test that protected routes redirect after logout"""
        # Logout
        page.click('[data-testid="user-menu"]')
        page.click('text=/logout/i')
        page.wait_for_url("**/auth/login")

        # Try to access protected route
        page.goto(f"{config.FRONTEND_BASE_URL}/dashboard/pipeline")

        # Should redirect to login
        page.wait_for_url("**/auth/login", timeout=config.NAVIGATION_TIMEOUT)


class TestAuthenticationPersistence:
    """Test authentication state persistence"""

    def test_auth_persists_across_page_reload(self, page: Page):
        """Test that user stays logged in after page reload"""
        # Register and login
        page.goto(f"{config.FRONTEND_BASE_URL}/auth/register")
        page.fill('input[name="full_name"]', config.TEST_USER_NAME)
        page.fill('input[name="email"]', f"persist-{config.TEST_USER_EMAIL}")
        page.fill('input[name="team_name"]', config.TEST_TEAM_NAME)
        page.fill('input[name="password"]', config.TEST_USER_PASSWORD)
        page.fill('input[name="confirmPassword"]', config.TEST_USER_PASSWORD)
        page.click('button[type="submit"]')

        page.wait_for_url("**/dashboard", timeout=config.NAVIGATION_TIMEOUT)

        # Reload page
        page.reload()

        # Should still be on dashboard (not redirected to login)
        expect(page).to_have_url(f"{config.FRONTEND_BASE_URL}/dashboard")

        # User menu should still be visible
        expect(page.locator('[data-testid="user-menu"]')).to_be_visible()

    def test_auth_persists_across_navigation(self, page: Page):
        """Test that user stays logged in when navigating"""
        # Register and login
        page.goto(f"{config.FRONTEND_BASE_URL}/auth/register")
        page.fill('input[name="full_name"]', config.TEST_USER_NAME)
        page.fill('input[name="email"]', f"nav-{config.TEST_USER_EMAIL}")
        page.fill('input[name="team_name"]', config.TEST_TEAM_NAME)
        page.fill('input[name="password"]', config.TEST_USER_PASSWORD)
        page.fill('input[name="confirmPassword"]', config.TEST_USER_PASSWORD)
        page.click('button[type="submit"]')

        page.wait_for_url("**/dashboard", timeout=config.NAVIGATION_TIMEOUT)

        # Navigate to different page
        page.click('text=/pipeline/i')
        page.wait_for_url("**/dashboard/pipeline")

        # User should still be logged in
        expect(page.locator('[data-testid="user-menu"]')).to_be_visible()

        # Navigate to another page
        page.click('text=/portfolio/i')
        page.wait_for_url("**/dashboard/portfolio")

        # Still logged in
        expect(page.locator('[data-testid="user-menu"]')).to_be_visible()


class TestPasswordVisibility:
    """Test password visibility toggle"""

    def test_password_visibility_toggle(self, page: Page):
        """Test showing/hiding password"""
        page.goto(f"{config.FRONTEND_BASE_URL}/auth/login")

        # Password should be hidden initially
        password_input = page.locator('input[type="password"]')
        expect(password_input).to_have_attribute("type", "password")

        # Click show password button (if exists)
        show_password_btn = page.locator('[data-testid="toggle-password-visibility"]')
        if show_password_btn.count() > 0:
            show_password_btn.click()

            # Should change to text input
            expect(page.locator('input[name="password"]')).to_have_attribute("type", "text")

            # Click again to hide
            show_password_btn.click()

            # Should change back to password
            expect(page.locator('input[name="password"]')).to_have_attribute("type", "password")
