# Real Estate OS Test Suite

Comprehensive test suite for the Real Estate OS platform covering integration tests, end-to-end tests, and unit tests.

## Test Structure

```
tests/
├── conftest.py                 # Shared fixtures and configuration
├── integration/                # Integration tests
│   ├── test_webhooks.py       # Webhook signature verification and processing
│   ├── test_idempotency.py    # Idempotency key handling
│   ├── test_sse.py            # Server-Sent Events real-time updates
│   ├── test_auth_and_ratelimiting.py  # Authentication and rate limiting
│   ├── test_reconciliation.py # Portfolio reconciliation
│   └── test_deliverability_compliance.py  # Email/SMS compliance
├── e2e/                        # End-to-end tests
│   ├── test_auth_flow.py      # User registration and login
│   ├── test_pipeline.py       # Pipeline management
│   └── test_memo_workflow.py  # Memo generation workflow
└── unit/                       # Unit tests
    └── (future unit tests)
```

## Installation

Install testing dependencies:

```bash
pip install -r requirements-test.txt
```

For E2E tests, install Playwright browsers:

```bash
playwright install
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Integration tests only
pytest tests/integration/

# E2E tests only
pytest tests/e2e/

# Specific test file
pytest tests/integration/test_webhooks.py

# Specific test class
pytest tests/integration/test_webhooks.py::TestWebhookSignatureVerification

# Specific test function
pytest tests/integration/test_webhooks.py::TestWebhookSignatureVerification::test_valid_signature_accepted
```

### Run Tests by Marker

```bash
# Run webhook tests
pytest -m webhook

# Run authentication tests
pytest -m auth

# Skip slow tests
pytest -m "not slow"

# Run only integration tests
pytest -m integration
```

### Parallel Execution

Run tests in parallel for faster execution:

```bash
# Run with 4 workers
pytest -n 4

# Run with auto-detected CPU count
pytest -n auto
```

### Coverage Reports

```bash
# Generate coverage report
pytest --cov=api --cov=db --cov-report=html

# View HTML report
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
```

## Test Categories

### Integration Tests

Test the integration between components, API endpoints, and database:

- **Webhooks**: Signature verification, payload handling, event processing
- **Idempotency**: Duplicate request detection, response caching
- **SSE**: Real-time event broadcasting, connection management
- **Authentication**: User login, JWT tokens, rate limiting, lockout
- **Reconciliation**: Portfolio metrics validation, drift detection
- **Compliance**: DNS validation, unsubscribe management, DNC lists, consent tracking

### E2E Tests

Test complete user workflows from browser perspective:

- **Authentication Flow**: Registration → Login → Dashboard access
- **Pipeline Management**: View properties → Drag-and-drop stage changes → View updates
- **Memo Workflow**: Select property → Choose template → Generate → Send → Verify delivery

### Unit Tests

Test individual functions and classes in isolation (future):

- Business logic functions
- Utility functions
- Data transformations

## Test Fixtures

Common fixtures available in `conftest.py`:

- `client`: FastAPI test client
- `test_db`: Test database session
- `test_team`: Sample team
- `test_user`: Sample admin user
- `test_agent_user`: Sample agent user
- `auth_headers`: Authentication headers for admin
- `agent_auth_headers`: Authentication headers for agent
- `test_property`: Sample property
- `test_properties`: Multiple sample properties across stages
- `mock_redis`: Mock Redis for rate limiting tests
- `mock_celery`: Mock Celery for task tests

## Writing Tests

### Integration Test Example

```python
def test_create_property(
    client: TestClient,
    auth_headers: dict,
    test_team: Team
):
    """Test creating a new property"""
    response = client.post(
        "/api/v1/properties",
        json={
            "team_id": test_team.id,
            "address": "123 Test St",
            "city": "Test City",
            "state": "CA",
            "zip_code": "12345",
            "bird_dog_score": 0.8
        },
        headers=auth_headers
    )

    assert response.status_code == 201
    data = response.json()

    assert data["address"] == "123 Test St"
    assert data["city"] == "Test City"
```

### E2E Test Example

```python
def test_user_login_flow(page: Page):
    """Test user can login successfully"""
    # Navigate to login page
    page.goto("http://localhost:3000/auth/login")

    # Fill in credentials
    page.fill('input[type="email"]', "test@example.com")
    page.fill('input[type="password"]', "testpassword123")

    # Submit form
    page.click('button[type="submit"]')

    # Should redirect to dashboard
    page.wait_for_url("**/dashboard")

    # Verify dashboard loaded
    assert "Pipeline" in page.content()
```

## Continuous Integration

Tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pytest --cov --junitxml=junit.xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Best Practices

1. **Test Isolation**: Each test should be independent and not rely on other tests
2. **Clean Database**: Use `test_db` fixture which creates fresh database per test
3. **Mock External Services**: Use mocks for Redis, Celery, email providers, etc.
4. **Descriptive Names**: Test names should clearly describe what is being tested
5. **AAA Pattern**: Arrange → Act → Assert
6. **Fast Tests**: Keep tests fast by using in-memory databases and minimal setup
7. **Coverage**: Aim for 70%+ code coverage

## Troubleshooting

### Tests Failing Due to Database

Ensure test database is clean:

```bash
# Tests use in-memory SQLite by default
# No cleanup needed
```

### SSE Tests Hanging

SSE tests may have longer timeouts for connection handling:

```bash
pytest tests/integration/test_sse.py --timeout=10
```

### E2E Tests Failing

Ensure frontend and backend are running:

```bash
# Terminal 1: Backend
cd /path/to/real-estate-os
uvicorn api.main:app --reload

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3: Tests
pytest tests/e2e/
```

## Performance

Test execution time benchmarks:

- Integration tests: ~30-60 seconds
- E2E tests: ~2-5 minutes
- Full suite: ~3-7 minutes
- Parallel (4 workers): ~1-2 minutes

## Contributing

When adding new features, please:

1. Write integration tests for API endpoints
2. Write E2E tests for user-facing workflows
3. Ensure coverage doesn't decrease
4. Run full test suite before committing

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Playwright Documentation](https://playwright.dev/python/)
