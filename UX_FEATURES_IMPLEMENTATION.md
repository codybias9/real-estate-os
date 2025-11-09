# UX Features Implementation Guide

## Overview

This document provides a comprehensive overview of the UX features implemented for Real Estate OS, aligned with the 6-month post-launch roadmap.

## Architecture

### Tech Stack
- **Backend**: FastAPI + SQLAlchemy + PostgreSQL
- **Database**: PostgreSQL 13+ with JSONB support
- **ORM**: SQLAlchemy 2.0
- **API Framework**: FastAPI with async support
- **Validation**: Pydantic v2

### Project Structure
```
api/
├── main.py              # FastAPI app entry point
├── database.py          # Database connection & session management
├── schemas.py           # Pydantic models for validation
└── routers/
    ├── properties.py    # Property management endpoints
    ├── quick_wins.py    # Quick Win features (Month 1)
    └── workflow.py      # Workflow automation (P0 features)

db/
├── models.py            # SQLAlchemy ORM models
└── versions/
    └── c9f3a8e1d4b2_*.py  # Alembic migration
```

---

## Database Schema

### Core Tables

#### 1. **users**
User accounts and authentication
- Role-based access control (admin, manager, agent, viewer)
- User settings and preferences
- Activity tracking

#### 2. **properties**
Enhanced property tracking with complete lifecycle management
- Core property info (address, APN, beds, baths, sqft)
- Owner information and contact details
- Pipeline stage tracking
- Scoring (bird_dog_score, probability_close, expected_value)
- Propensity signals ("Likely to entertain offer")
- Data quality tracking and provenance
- Engagement metrics (touches, replies)
- Document URLs (memo, packet)

#### 3. **pipeline_stages**
Configurable pipeline stages
- Customizable stage definitions
- Color coding and ordering
- Stage-specific configuration (SLAs, auto-actions)

#### 4. **communications**
All communications with email threading
- Email, SMS, call, postcard, note support
- Thread tracking (thread_id, message_id, in_reply_to)
- Engagement tracking (sent, delivered, opened, clicked, replied)
- Call-specific fields (duration, recording, transcription, sentiment)
- Template linkage

#### 5. **templates**
Stage-aware email/SMS templates
- Template content (subject, body_text, body_html)
- Stage restrictions (allowed_stages)
- Performance tracking (send_count, open_count, reply_count)
- A/B testing support (variant_group, is_champion)

#### 6. **tasks**
Task management with SLA and assignment
- Assignment and priority
- SLA tracking with due dates
- Source tracking (created from which event)
- Status (pending, in_progress, completed, overdue)

#### 7. **timeline_events**
Activity timeline for properties
- Event type categorization
- User attribution
- Related entity linking

#### 8. **deals**
Deal tracking with economics
- Offer price, assignment fee, margin tracking
- Probability of close with factors
- Expected value calculation (margin × probability)
- Investor information
- Timeline tracking

#### 9. **next_best_actions**
AI-generated action recommendations
- Action type and description
- Priority scoring (0-1)
- Reasoning and signals
- Completion tracking

#### 10. **smart_lists**
Saved search criteria for dynamic filtering
- JSON filter configuration
- Cached property counts
- Sharing support

#### 11. **data_flags**
User-reported data quality issues
- Field-level issue tracking
- Suggested corrections
- Resolution workflow

#### 12. **compliance_records**
DNC, opt-outs, and consent tracking
- Phone and email compliance
- Active status and expiration

#### 13. **deliverability_metrics**
Email deliverability tracking
- Daily metrics per sender
- Bounce, spam, open, click rates
- Reputation scoring
- Alert management

---

## API Endpoints

### Base URL
All endpoints are prefixed with `/api/v1`

---

## 1. Workflow Accelerators

### Next Best Action (NBA) - P0 Feature

**Purpose**: Surface the ONE thing to do next on each property, driven by stage, freshness, and recent activity.

#### Endpoints

```
GET /api/v1/workflow/next-best-actions
```
Get NBA recommendations for properties
- Query params: property_id, is_completed, limit
- Returns: List of NBAs sorted by priority_score

```
POST /api/v1/workflow/next-best-actions/generate
```
Generate NBA recommendations
- Body: { property_id?, force_regenerate? }
- Returns: Generation statistics

**NBA Generation Rules**:
1. **Outreach with no reply > 7 days** → "Send follow-up" (priority: 0.8)
2. **High score (>0.7) with no memo** → "Generate memo" (priority: 0.9)
3. **Negotiation without packet** → "Send packet" (priority: 0.95)
4. **Warm replies in last 48h** → "Respond to warm lead" (priority: 1.0)
5. **Stalled in stage > 14 days** → "Move or archive" (priority: 0.6)

```
POST /api/v1/workflow/next-best-actions/{action_id}/execute
```
Execute an NBA
- Marks action as completed
- Creates timeline event

```
POST /api/v1/workflow/next-best-actions/{action_id}/dismiss
```
Dismiss an NBA without executing

---

### Smart Lists - P0 Feature

**Purpose**: Saved search criteria that create dynamic property views (e.g., "Hot & Ready", "Warm Replies", "Stuck Deals").

#### Endpoints

```
GET /api/v1/workflow/smart-lists
```
List all smart lists
- Query params: user_id, include_shared
- Returns: List of smart lists with cached counts

```
POST /api/v1/workflow/smart-lists
```
Create a new smart list
- Body: SmartListCreate schema
- Returns: Created smart list with initial count

**Filter Examples**:
```json
{
  "name": "High Score & No Memo",
  "filters": {
    "bird_dog_score__gte": 0.7,
    "memo_url__is_null": true
  }
}

{
  "name": "Warm Replies Last 48h",
  "filters": {
    "last_reply_date__gte": "2025-11-01T00:00:00Z"
  }
}

{
  "name": "Stalled in Outreach 7+ Days",
  "filters": {
    "current_stage": "outreach",
    "last_contact_days_ago_gte": 7
  }
}
```

```
GET /api/v1/workflow/smart-lists/{list_id}/properties
```
Get properties matching a smart list
- Applies saved filters
- Supports pagination
- Returns: PropertyListResponse

```
POST /api/v1/workflow/smart-lists/{list_id}/refresh
```
Refresh property count cache

---

### One-Click Tasking - P1 Feature

**Purpose**: Convert events (reply, open, call) into tasks with SLA and assignee.

#### Endpoint

```
POST /api/v1/workflow/create-task-from-event
```
Create task from an event
- Body: { event_type, event_id, assignee_id, sla_hours }
- Event types: "communication", "timeline_event"
- Returns: Created task

---

## 2. Quick Wins (Month 1)

### Quick Win #1: Generate & Send Combo

**Purpose**: One-click from PDF generation → sent email.

#### Endpoint

```
POST /api/v1/quick-wins/generate-and-send
```
Generate packet and send in one action

**Request**:
```json
{
  "property_id": 123,
  "template_id": 5,
  "to_email": "investor@example.com",
  "regenerate_memo": false
}
```

**What it does**:
1. Optionally regenerates investor memo
2. Generates full packet (memo + comps + disclosures)
3. Renders template with property data
4. Sends email with packet attached
5. Creates communication record
6. Updates property.last_contact_date
7. Increments template.send_count
8. Creates timeline event

---

### Quick Win #2: Auto-Assign on Reply

**Purpose**: Automatically assign property to user when they receive a reply.

#### Endpoint

```
POST /api/v1/quick-wins/auto-assign-on-reply/{communication_id}
```
Auto-assign property on inbound reply

**Body**:
```json
{
  "assignee_id": 42
}
```

**What it does**:
1. Verifies communication is inbound reply
2. Checks if property is unassigned
3. Assigns to specified user
4. Updates property.last_reply_date
5. Increments property.reply_count
6. Creates timeline event
7. Creates high-priority follow-up task (24h SLA)

---

### Quick Win #3: Stage-Aware Templates

**Purpose**: Filter templates by current stage to prevent wrong template selection.

#### Endpoint

```
GET /api/v1/quick-wins/templates/for-stage/{stage}
```
Get templates allowed for a specific stage

**Query params**:
- `stage`: Pipeline stage (e.g., "outreach", "negotiation")
- `type`: Communication type (email, sms, etc.)

**What it does**:
1. Filters active templates
2. Matches communication type
3. Checks allowed_stages (empty = all stages allowed)
4. Calculates performance metrics (open_rate, reply_rate)

**Response**:
```json
[
  {
    "id": 1,
    "name": "Initial Outreach",
    "type": "email",
    "allowed_stages": ["prospect", "outreach"],
    "send_count": 150,
    "open_rate": 0.42,
    "reply_rate": 0.15
  }
]
```

---

### Quick Win #4: Flag Data Issue

**Purpose**: Crowdsource data quality fixes by allowing users to report issues.

#### Endpoints

```
POST /api/v1/quick-wins/flag-data-issue
```
Report a data quality issue

**Request**:
```json
{
  "property_id": 123,
  "field_name": "owner_phone",
  "issue_type": "incorrect",
  "description": "Phone number disconnected",
  "suggested_value": "555-0100"
}
```

**What it does**:
1. Creates DataFlag record
2. Adds issue to property.data_flags JSON array
3. Decrements property.data_quality_score
4. Creates timeline event

```
GET /api/v1/quick-wins/data-flags
```
List data quality flags
- Query params: status (open/resolved), property_id

```
PATCH /api/v1/quick-wins/data-flags/{flag_id}/resolve
```
Resolve a data flag
- Optionally apply suggested value
- Creates timeline event if value applied

---

## 3. Property Management

### Property CRUD

```
GET /api/v1/properties
```
List properties with advanced filtering

**Query Parameters**:
- `page`, `page_size`: Pagination
- `current_stage`: Filter by stage(s)
- `assigned_user_id`: Filter by assignee
- `bird_dog_score_gte`, `bird_dog_score_lte`: Score range
- `has_memo`: Boolean
- `has_reply`: Boolean
- `last_contact_days_ago_gte`: Not contacted in X days
- `search`: Full-text search (address, owner, city)
- `tags`: Filter by tags
- `sort_by`, `sort_desc`: Sorting

```
GET /api/v1/properties/{property_id}
```
Get single property

```
POST /api/v1/properties
```
Create property

```
PATCH /api/v1/properties/{property_id}
```
Update property

```
POST /api/v1/properties/{property_id}/stage
```
Update pipeline stage
- Creates stage history record
- Creates timeline event

```
DELETE /api/v1/properties/{property_id}
```
Archive property (soft delete)

---

### Property Timeline & History

```
GET /api/v1/properties/{property_id}/timeline
```
Get activity timeline
- Returns chronological list of all activity
- Limit: 100 events default

```
GET /api/v1/properties/{property_id}/stage-history
```
Get stage transition history

---

### Pipeline Statistics

```
GET /api/v1/properties/stats/pipeline
```
Get pipeline overview

**Response**:
```json
{
  "total_properties": 1250,
  "by_stage": {
    "prospect": 300,
    "outreach": 450,
    "negotiation": 200,
    "won": 150,
    "lost": 150
  },
  "avg_days_in_stage": {
    "prospect": 3.5,
    "outreach": 12.8,
    "negotiation": 7.2
  },
  "conversion_rates": {
    "prospect_to_outreach": 0.75,
    "outreach_to_contact": 0.33
  }
}
```

---

## 4. Health & Status

```
GET /healthz
```
Basic health check

```
GET /readyz
```
Readiness check (includes database connectivity)

```
GET /api/v1/status
```
API status with statistics

**Response**:
```json
{
  "status": "operational",
  "statistics": {
    "properties": 1250,
    "users": 15,
    "communications": 4500,
    "tasks": 320
  },
  "features": {
    "quick_wins": {
      "generate_and_send": true,
      "auto_assign_on_reply": true,
      "stage_aware_templates": true,
      "flag_data_issue": true
    },
    "workflow": {
      "next_best_actions": true,
      "smart_lists": true,
      "one_click_tasking": true
    }
  }
}
```

---

## Implementation Status

### ✅ Implemented (Current)

**Database**:
- ✅ Complete schema with 20+ tables
- ✅ Alembic migration ready
- ✅ SQLAlchemy models with relationships
- ✅ JSONB support for flexible metadata
- ✅ Indexes for performance

**API**:
- ✅ FastAPI application with lifespan management
- ✅ Database session dependency injection
- ✅ Pydantic schemas for validation
- ✅ CORS and middleware support
- ✅ Global error handling

**Quick Wins** (Month 1):
- ✅ Generate & Send Combo
- ✅ Auto-Assign on Reply
- ✅ Stage-Aware Templates
- ✅ Flag Data Issue

**Workflow** (P0):
- ✅ Next Best Action panel
- ✅ Smart Lists with dynamic filtering
- ✅ One-Click Tasking

**Property Management**:
- ✅ Full CRUD operations
- ✅ Advanced filtering and search
- ✅ Pipeline stage management
- ✅ Timeline and history tracking
- ✅ Pipeline statistics

### 🚧 TODO (Next Phases)

**Q1 Features**:
- ⏳ Email threading (Gmail/O365 integration)
- ⏳ Call capture + transcription (Twilio integration)
- ⏳ AI reply drafting
- ⏳ Mobile quick actions

**Q2 Features**:
- ⏳ Deal Economics panel with what-if scenarios
- ⏳ Investor Readiness Score
- ⏳ Template Leaderboard with A/B testing
- ⏳ Secure Share Links for investors
- ⏳ Deal Room export (ZIP)
- ⏳ Owner Propensity Signals (ML model)
- ⏳ Provenance Inspector
- ⏳ Deliverability Dashboard
- ⏳ Cadence Governor (auto-pause, switch channel)
- ⏳ Compliance Pack (DNC, disclaimers)
- ⏳ Budget Monitor

---

## Usage Examples

### Example 1: Creating a Smart List for "Hot Prospects"

```python
import requests

# Create smart list
response = requests.post("http://localhost:8000/api/v1/workflow/smart-lists", json={
    "name": "Hot Prospects - Ready to Contact",
    "description": "High-scoring properties with no recent contact",
    "icon": "🔥",
    "color": "#FF5722",
    "filters": {
        "bird_dog_score__gte": 0.7,
        "current_stage__in": ["prospect", "enrichment", "scored"],
        "last_contact_days_ago_gte": 7,
        "memo_url__is_null": false
    }
})

list_id = response.json()["id"]

# Get properties in this list
properties = requests.get(
    f"http://localhost:8000/api/v1/workflow/smart-lists/{list_id}/properties"
)
```

### Example 2: Generate & Send Workflow

```python
# Generate packet and send to investor
response = requests.post("http://localhost:8000/api/v1/quick-wins/generate-and-send", json={
    "property_id": 123,
    "template_id": 5,
    "to_email": "investor@example.com",
    "regenerate_memo": True  # Force regeneration of memo
})

print(f"Packet sent: {response.json()['packet_url']}")
print(f"Email ID: {response.json()['communication_id']}")
```

### Example 3: Processing Inbound Reply

```python
# When webhook receives an inbound email reply
communication_id = 456  # From email webhook

# Auto-assign to user
response = requests.post(
    f"http://localhost:8000/api/v1/quick-wins/auto-assign-on-reply/{communication_id}",
    json={"assignee_id": 42}
)

if response.json()["success"]:
    print(f"Property assigned to user {response.json()['assigned_user_id']}")
    print("Follow-up task created with 24h SLA")
```

### Example 4: Generating Next Best Actions

```python
# Generate NBAs for all properties
response = requests.post(
    "http://localhost:8000/api/v1/workflow/next-best-actions/generate"
)

print(f"Generated {response.json()['actions_generated']} actions")

# Get top priority actions
nbas = requests.get(
    "http://localhost:8000/api/v1/workflow/next-best-actions?limit=10"
).json()

for nba in nbas:
    print(f"Priority {nba['priority_score']}: {nba['title']}")
    print(f"  Reasoning: {nba['reasoning']}")
```

---

## Database Migration

### Running the Migration

```bash
# Using Alembic (if installed)
cd /home/user/real-estate-os/db
alembic upgrade head

# Manual SQL execution
psql $DB_DSN -f versions/c9f3a8e1d4b2_add_ux_feature_models.py
```

### Tables Created
- users
- pipeline_stages
- properties
- property_stage_history
- templates
- communications
- tasks
- timeline_events
- deals
- deal_documents
- investor_shares
- data_flags
- smart_lists
- next_best_actions
- compliance_records
- deliverability_metrics
- cadence_rules
- budget_monitors

---

## Performance Considerations

### Indexes
All key query patterns are indexed:
- properties: stage + assigned_user, score, created_at, APN
- communications: property_id + type, thread_id, sent_at
- tasks: assignee_id + status, due_date
- next_best_actions: property_id + is_completed

### JSONB Usage
JSONB columns for flexible metadata:
- property.propensity_factors
- property.data_sources
- communication.metadata
- task.metadata
- deal.probability_factors
- template.allowed_stages

### Caching
- Smart list property counts (refreshable)
- Template performance metrics (updated on send)
- Pipeline statistics (computed on demand)

---

## Security Considerations

### TODO: Authentication
- Implement OAuth2/JWT for API authentication
- Add user context to all endpoints (currently hardcoded user_id=1)
- Role-based access control enforcement

### Data Protection
- Compliance records table for DNC/opt-out
- Audit trail via timeline_events
- Soft deletes (archived_at) to preserve data

---

## Testing

### Manual Testing
```bash
# Start the API
cd /home/user/real-estate-os
poetry run uvicorn api.main:app --reload

# Access interactive docs
open http://localhost:8000/docs
```

### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

---

## Deployment

### Environment Variables
```bash
DB_DSN=postgresql://user:password@localhost:5432/realestateos
ENVIRONMENT=production
CORS_ORIGINS=https://app.example.com
DEBUG=false
LOG_LEVEL=info
```

### Docker Deployment
Already configured in existing infrastructure:
- Image: `codybias9/reo-api:0.1.3` (update version)
- Port: 8000
- Health checks: `/healthz`, `/readyz`

---

## Next Steps

### Immediate (Week 1)
1. Test migration on dev database
2. Populate sample data for testing
3. Integration testing with existing scraper pipeline
4. Deploy updated API

### Short-term (Month 1)
1. Implement remaining routers (communications, templates, tasks, deals)
2. Add authentication and authorization
3. Build frontend UI for Quick Wins
4. Email webhook integration for auto-assign

### Medium-term (Q1)
1. Email threading (Gmail/O365 integration)
2. Call capture with Twilio
3. Mobile API endpoints
4. AI reply drafting

### Long-term (Q2)
1. Deal Economics panel
2. ML-based propensity scoring
3. Cadence automation
4. Compliance dashboard
5. Template A/B testing
