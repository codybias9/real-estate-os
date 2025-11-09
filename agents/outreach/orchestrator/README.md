# Outreach.Orchestrator

**Single-Writer Agent**: Orchestrates property owner outreach via email.

## Purpose

Outreach.Orchestrator is responsible for:
- Creating outreach campaigns for property owners
- Sending personalized investment opportunity emails via SendGrid
- Tracking campaign status (sent, delivered, opened, clicked, responded)
- Handling SendGrid webhooks for real-time status updates
- Providing campaign analytics and statistics

## Architecture

**Input Contracts**: `PropertyRecord`, `ScoreResult`, memo URL
**Output**: Email campaigns via SendGrid
**Events Published**: `event.outreach.scheduled`, `event.outreach.sent`

## Usage

### Initialize Orchestrator

```python
from orchestrator import OutreachOrchestrator
from orchestrator.repository import OutreachRepository

# Initialize repository
repo = OutreachRepository()  # Reads DB_DSN from environment

# Initialize orchestrator
orchestrator = OutreachOrchestrator(
    repository=repo,
    sendgrid_api_key="your-api-key",  # Or set SENDGRID_API_KEY env var
    from_email="team@yourcompany.com",
    from_name="Real Estate Team",
)
```

### Create Campaign

```python
# Create campaign (idempotent)
campaign = orchestrator.create_campaign(
    tenant_id="tenant-uuid",
    property_record=property.dict(),  # PropertyRecord
    score_result=score.dict(),  # ScoreResult
    memo_url="https://s3.../memo.pdf",
)

print(f"Campaign ID: {campaign.id}")
print(f"Status: {campaign.status}")
```

### Send Campaign

```python
# Send email via SendGrid
result = orchestrator.send_campaign(
    campaign_id=campaign.id,
    tenant_id="tenant-uuid",
    property_record=property.dict(),
    score_result=score.dict(),
)

print(f"Status: {result['status']}")
print(f"Message ID: {result['message_id']}")
```

### Handle Webhooks

```python
# In your API endpoint for SendGrid webhooks
@app.post("/webhooks/sendgrid")
async def handle_sendgrid_webhook(data: dict):
    result = orchestrator.handle_webhook(data)
    if result:
        print(f"Campaign {result['campaign_id']}: {result['event_type']}")
    return {"ok": True}
```

## Features

### 1. Campaign Lifecycle

```
scheduled → sent → delivered → opened → clicked → responded
                → bounced
                → failed
```

### 2. Idempotent Campaign Creation

Creating a campaign for the same property multiple times returns the existing campaign:

```python
campaign1 = orchestrator.create_campaign(...)
campaign2 = orchestrator.create_campaign(...)  # Same property

assert campaign1.id == campaign2.id  # ✓ Same campaign
```

### 3. Email Templates

**HTML Template**: Professional, responsive design with:
- Property summary card
- Investment score badge
- Top 3 scoring reasons
- Call-to-action button to view memo
- Company branding

**Plain Text Template**: Fallback for email clients that don't support HTML

### 4. SendGrid Integration

- Personalized emails (To: owner name and email)
- Custom tracking arguments (campaign_id, tenant_id, property_id)
- Webhook support for delivery tracking
- Error handling and retry logic

### 5. Webhook Events

Supported webhook events:
- `delivered`: Email successfully delivered
- `open`: Recipient opened email
- `click`: Recipient clicked link in email
- `bounce`: Email bounced
- `unsubscribe`: Recipient unsubscribed

### 6. Campaign Analytics

```python
# Get statistics
stats = orchestrator.get_statistics("tenant-uuid")
print(f"Sent: {stats.get('sent', 0)}")
print(f"Opened: {stats.get('opened', 0)}")
print(f"Clicked: {stats.get('clicked', 0)}")

# Get campaigns by status
sent_campaigns = orchestrator.get_campaigns_by_status(
    OutreachStatus.SENT,
    "tenant-uuid",
    limit=10
)
```

## Database Schema

### outreach_campaigns

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| tenant_id | UUID | Tenant isolation |
| property_id | UUID | Property reference |
| owner_name | String | Property owner name |
| owner_email | String | Property owner email |
| status | String | Campaign status |
| subject | String | Email subject line |
| memo_url | Text | URL to memo PDF |
| sendgrid_message_id | String | SendGrid tracking ID |
| scheduled_at | Timestamp | When to send |
| sent_at | Timestamp | When sent |
| delivered_at | Timestamp | When delivered |
| opened_at | Timestamp | When opened |
| clicked_at | Timestamp | When clicked |
| responded_at | Timestamp | When responded |

### outreach_events

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| campaign_id | UUID | Campaign reference |
| event_type | String | Event type (sent, opened, etc.) |
| event_data | JSON | SendGrid webhook data |
| occurred_at | Timestamp | Event timestamp |

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=orchestrator --cov-report=html

# Run specific test
pytest tests/test_orchestrator.py::TestEmailSending -v
```

## Dependencies

- **sendgrid**: Email delivery API
- **jinja2**: Template rendering
- **sqlalchemy**: ORM for campaign tracking
- **python-dateutil**: Timezone handling

## Configuration

Set these environment variables:

```bash
# Required
export SENDGRID_API_KEY="your-api-key"
export DB_DSN="postgresql://user:pass@localhost/db"

# Optional
export SENDGRID_FROM_EMAIL="team@yourcompany.com"
export SENDGRID_FROM_NAME="Your Company Team"
```

## Template Customization

Templates are located in `templates/` directory:
- `memo_delivery_email.html` - HTML email template
- `memo_delivery_email.txt` - Plain text email template

Customize with your own branding, logos, and messaging.

## Error Handling

- **SendGrid API failures**: Campaign status set to `failed`, error logged
- **Missing owner email**: Raises `ValueError`
- **Campaign not found**: Raises `ValueError`
- **Already sent**: Returns existing message ID (idempotent)

## Best Practices

1. **Test emails first**: Use SendGrid sandbox mode for testing
2. **Monitor webhooks**: Set up SendGrid webhook endpoint for tracking
3. **Respect unsubscribes**: Check campaign status before sending
4. **Rate limiting**: SendGrid has rate limits, implement queuing for bulk sends
5. **Email validation**: Validate owner emails before creating campaigns
