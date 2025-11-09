"""
Playwright Configuration for E2E Tests
"""
from playwright.sync_api import Page
import os

# Base URLs
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")

# Timeouts
DEFAULT_TIMEOUT = 30000  # 30 seconds
NAVIGATION_TIMEOUT = 60000  # 60 seconds

# Browser options
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
SLOW_MO = int(os.getenv("SLOW_MO", "0"))  # Slow down operations by N milliseconds

# Screenshot/video settings
SCREENSHOT_ON_FAILURE = True
VIDEO_ON_FAILURE = True

# Test data
TEST_USER_EMAIL = "e2e-test@example.com"
TEST_USER_PASSWORD = "E2eTestPassword123!"
TEST_USER_NAME = "E2E Test User"
TEST_TEAM_NAME = "E2E Test Team"
