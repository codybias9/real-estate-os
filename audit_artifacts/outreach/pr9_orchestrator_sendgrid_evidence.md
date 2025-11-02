# PR9: Outreach.Orchestrator + SendGrid - Evidence Pack

**PR**: `feat/outreach-orchestrator-sendgrid`
**Date**: 2025-11-02
**Branch**: `claude/realestate-audit-canvas-011CUjnrkmyeMSTozDmpy6xx`

## Summary

Implemented Outreach.Orchestrator agent for property owner outreach via personalized email campaigns using SendGrid API integration.

## What Was Built

### 1. Email Templates

**HTML Template** (`templates/memo_delivery_email.html`, 124 lines):
- Responsive design with professional styling
- Property summary card with investment score
- Top 3 scoring reasons with color-coded badges
- Call-to-action button to view memo PDF
- Company branding and unsubscribe footer

**Plain Text Template** (`templates/memo_delivery_email.txt`, 33 lines):
- Fallback for email clients without HTML support
- All key information in plain text format

### 2. Database Models

**File**: `src/orchestrator/models.py` (106 lines)

**Tables**:
- `outreach_campaigns`: Campaign tracking with owner contact info
- `outreach_events`: Immutable event log (sent, opened, clicked, etc.)

**Campaign Statuses**:
- scheduled, sent, delivered, opened, clicked, responded, bounced, unsubscribed, failed

### 3. OutreachOrchestrator Agent

**File**: `src/orchestrator/orchestrator.py` (356 lines)

**Key Methods**:

#### `create_campaign(tenant_id, property_record, score_result, memo_url)`
Creates outreach campaign with idempotency check:
- Extracts owner email from property record
- Generates personalized subject line
- Checks for existing campaign (idempotent)
- Stores in database with scheduled status

#### `send_campaign(campaign_id, tenant_id, property_record, score_result)`
Sends email via SendGrid:
- Renders HTML and plain text templates
- Creates SendGrid email with personalization
- Adds custom tracking args (campaign_id, tenant_id, property_id)
- Updates campaign status to "sent"
- Logs event in audit trail
- Returns message ID for tracking

#### `handle_webhook(webhook_data)`
Processes SendGrid webhook events:
- Maps webhook events to campaign statuses
- Updates timestamps (delivered_at, opened_at, clicked_at)
- Logs all events for audit trail
- Supports: delivered, open, click, bounce, unsubscribe

**Features**:
- Template rendering with Jinja2
- SendGrid API integration with error handling
- Campaign analytics and statistics
- Idempotent operations
- Tenant isolation

### 4. Repository Layer

**File**: `src/orchestrator/repository.py` (334 lines)

**Methods**:
- `create_campaign()`: Create campaign with context
- `get_campaign()`: Retrieve by ID
- `get_campaign_by_property()`: Find campaign for property
- `update_campaign_status()`: Update status and timestamps
- `log_event()`: Immutable event logging
- `get_campaigns_by_status()`: Filter campaigns
- `count_by_status()`: Statistics per tenant

## Test Results

**Test Suite**: 23 tests, 100% passing
**Coverage**: 71% total (98% for orchestrator logic, 21% for repository due to mocking)

**Test Classes**:
- TestCampaignCreation (5 tests): Campaign creation, idempotency, validation
- TestEmailSending (4 tests): SendGrid integration, error handling
- TestWebhookHandling (6 tests): Webhook event processing
- TestTemplateRendering (2 tests): HTML/text template rendering
- TestCampaignQueries (4 tests): Campaign lookups and statistics
- TestOutreachCampaign (2 tests): Wrapper class functionality

**Key Test Coverage**:
- ✓ Campaign creation with idempotency
- ✓ Email sending via mocked SendGrid
- ✓ SendGrid API failure handling
- ✓ Webhook event processing (delivered, opened, clicked, bounced)
- ✓ Template rendering with property and score data
- ✓ Campaign queries and statistics
- ✓ Error cases (missing email, campaign not found)

## Files Created

- `agents/outreach/orchestrator/pyproject.toml` (48 lines)
- `agents/outreach/orchestrator/README.md` (253 lines)
- `agents/outreach/orchestrator/src/orchestrator/__init__.py` (6 lines)
- `agents/outreach/orchestrator/src/orchestrator/models.py` (106 lines)
- `agents/outreach/orchestrator/src/orchestrator/repository.py` (334 lines)
- `agents/outreach/orchestrator/src/orchestrator/orchestrator.py` (356 lines)
- `agents/outreach/orchestrator/templates/memo_delivery_email.html` (124 lines)
- `agents/outreach/orchestrator/templates/memo_delivery_email.txt` (33 lines)
- `agents/outreach/orchestrator/tests/conftest.py` (99 lines)
- `agents/outreach/orchestrator/tests/test_orchestrator.py` (497 lines)

**Total**: 1,856 lines

## Architectural Decisions

### 1. SendGrid Over SMTP
**Decision**: Use SendGrid API instead of direct SMTP

**Rationale**:
- Better deliverability (dedicated IPs, reputation management)
- Built-in webhook support for tracking
- Simple API integration
- Scales to high volume
- Email analytics included

### 2. Idempotent Campaign Creation
**Decision**: One campaign per property (check before create)

**Rationale**:
- Prevents duplicate emails to same owner
- Safe for event replay
- Reduces spam complaints
- Enables campaign history tracking

### 3. Template-Based Email
**Decision**: Jinja2 templates instead of hardcoded HTML

**Rationale**:
- Easy customization per tenant
- Separates content from logic
- A/B testing support
- Non-developers can edit templates
- HTML + plain text fallback

### 4. Webhook-Based Tracking
**Decision**: Use SendGrid webhooks instead of polling

**Rationale**:
- Real-time status updates
- Lower latency
- Reduces API calls
- Event-driven architecture
- Immutable audit trail

### 5. Campaign Status State Machine
**Decision**: Explicit status transitions

**Rationale**:
- Clear campaign lifecycle
- Easy to query (e.g., "show all opened")
- Prevents invalid state transitions
- Analytics and reporting

## Usage Example

```python
from orchestrator import OutreachOrchestrator, OutreachStatus
from orchestrator.repository import OutreachRepository

# Initialize
repo = OutreachRepository()
orchestrator = OutreachOrchestrator(
    repository=repo,
    sendgrid_api_key="your-key",
    from_email="team@company.com",
)

# Create campaign
campaign = orchestrator.create_campaign(
    tenant_id="tenant-uuid",
    property_record=property.dict(),
    score_result=score.dict(),
    memo_url="https://s3.../memo.pdf",
)

# Send email
result = orchestrator.send_campaign(
    campaign_id=campaign.id,
    tenant_id="tenant-uuid",
    property_record=property.dict(),
    score_result=score.dict(),
)
# → Email sent via SendGrid, status = "sent"

# Handle webhook (in API endpoint)
orchestrator.handle_webhook({
    "event": "open",
    "campaign_id": campaign.id,
    "tenant_id": "tenant-uuid",
})
# → Campaign status updated to "opened", timestamp recorded

# Get statistics
stats = orchestrator.get_statistics("tenant-uuid")
# → {"scheduled": 10, "sent": 5, "opened": 2, "clicked": 1}
```

## Integration Points

### Input Events
- `event.docgen.memo` → Triggers campaign creation
  - Property has memo ready
  - Create campaign and schedule send

### Output Events
- `event.outreach.scheduled` → Campaign created
- `event.outreach.sent` → Email sent
- `event.outreach.opened` → Email opened
- `event.outreach.clicked` → Link clicked
- `event.outreach.response` → Owner responded

### Dependencies
- **SendGrid API**: Email delivery
- **Docgen.Memo**: Provides memo URL
- **Pipeline.State**: Updates state to "outreach_pending" → "contacted"

## Testing Highlights

### Mock SendGrid
```python
@pytest.fixture
def mock_sendgrid():
    with patch("orchestrator.orchestrator.SendGridAPIClient") as mock_sg:
        client = MagicMock()
        mock_sg.return_value = client

        response = MagicMock()
        response.status_code = 202
        response.headers = {"X-Message-Id": "test-msg-id"}
        client.send.return_value = response

        yield client
```

### Webhook Testing
```python
def test_handle_webhook_opened(orchestrator):
    webhook_data = {
        "event": "open",
        "campaign_id": campaign_id,
        "tenant_id": tenant_id,
    }

    result = orchestrator.handle_webhook(webhook_data)

    assert result["event_type"] == "open"
    assert result["status"] == "opened"
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| SendGrid rate limits | Queue campaigns, implement throttling |
| Email bounces | Track bounce rate, validate emails before send |
| Spam complaints | Clear unsubscribe link, only send to engaged users |
| SendGrid outages | Retry logic, fallback to SMTP |
| Template rendering errors | Validate data before rendering, graceful fallbacks |
| Webhook replay | Idempotent webhook handling (check timestamps) |

## Next Steps

**PR10**: Collab.Timeline
- Single-writer timeline for collaboration events
- Markdown + attachments
- Property-level activity stream
- Real-time updates via SSE
