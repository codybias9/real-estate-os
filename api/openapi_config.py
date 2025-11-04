"""
OpenAPI Configuration and Examples
Enhances FastAPI auto-generated documentation with detailed examples
"""
from typing import Dict, Any

# ============================================================================
# REQUEST/RESPONSE EXAMPLES
# ============================================================================

OPENAPI_EXAMPLES = {
    # ========================================================================
    # AUTHENTICATION
    # ========================================================================
    "auth_register_request": {
        "summary": "Register New Team",
        "description": "Create a new account with team and admin user",
        "value": {
            "full_name": "John Doe",
            "email": "john@example.com",
            "password": "SecurePassword123!",
            "team_name": "Acme Real Estate"
        }
    },
    "auth_register_response": {
        "summary": "Successful Registration",
        "value": {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "user": {
                "id": 1,
                "full_name": "John Doe",
                "email": "john@example.com",
                "team_id": 1,
                "role": "admin",
                "created_at": "2024-01-15T10:30:00Z"
            },
            "team": {
                "id": 1,
                "name": "Acme Real Estate",
                "created_at": "2024-01-15T10:30:00Z"
            }
        }
    },
    "auth_login_request": {
        "summary": "Login",
        "value": {
            "email": "john@example.com",
            "password": "SecurePassword123!"
        }
    },
    "auth_login_response": {
        "summary": "Successful Login",
        "value": {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "user": {
                "id": 1,
                "full_name": "John Doe",
                "email": "john@example.com",
                "team_id": 1,
                "role": "admin"
            }
        }
    },

    # ========================================================================
    # PROPERTIES
    # ========================================================================
    "property_create_request": {
        "summary": "Add Property to Pipeline",
        "description": "Create a new property with all required fields",
        "value": {
            "address": "123 Main St",
            "city": "San Francisco",
            "state": "CA",
            "zip_code": "94102",
            "owner_name": "Jane Smith",
            "team_id": 1,
            "assigned_user_id": 1,
            "bird_dog_score": 0.85,
            "estimated_value": 850000,
            "tags": ["high-priority", "owner-occupied"]
        }
    },
    "property_response": {
        "summary": "Property Details",
        "value": {
            "id": 1,
            "address": "123 Main St",
            "city": "San Francisco",
            "state": "CA",
            "zip_code": "94102",
            "owner_name": "Jane Smith",
            "owner_phone": "+1-555-0100",
            "owner_email": "jane@example.com",
            "team_id": 1,
            "assigned_user_id": 1,
            "current_stage": "outreach",
            "stage_changed_at": "2024-01-15T10:30:00Z",
            "bird_dog_score": 0.85,
            "estimated_value": 850000,
            "memo_generated": True,
            "memo_sent_at": "2024-01-15T11:00:00Z",
            "owner_replied": False,
            "last_contact_at": "2024-01-15T11:00:00Z",
            "tags": ["high-priority", "owner-occupied"],
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T11:00:00Z"
        }
    },
    "property_list_response": {
        "summary": "List of Properties",
        "value": [
            {
                "id": 1,
                "address": "123 Main St",
                "city": "San Francisco",
                "state": "CA",
                "current_stage": "outreach",
                "bird_dog_score": 0.85,
                "estimated_value": 850000,
                "tags": ["high-priority"]
            },
            {
                "id": 2,
                "address": "456 Oak Ave",
                "city": "Oakland",
                "state": "CA",
                "current_stage": "new",
                "bird_dog_score": 0.72,
                "estimated_value": 650000,
                "tags": ["distressed"]
            }
        ]
    },
    "property_update_request": {
        "summary": "Update Property Stage",
        "description": "Move property to different pipeline stage",
        "value": {
            "current_stage": "qualified",
            "assigned_user_id": 2
        }
    },

    # ========================================================================
    # COMMUNICATIONS
    # ========================================================================
    "memo_generate_request": {
        "summary": "Generate Memo",
        "description": "Generate personalized memo using AI template",
        "value": {
            "property_id": 1,
            "template_id": 1,
            "send_immediately": True,
            "delivery_method": "email"
        }
    },
    "memo_generate_response": {
        "summary": "Generated Memo",
        "value": {
            "communication_id": 1,
            "property_id": 1,
            "template_id": 1,
            "subject": "Quick question about 123 Main St",
            "body": "Hi Jane,\n\nI noticed your property at 123 Main St...",
            "delivery_method": "email",
            "status": "sent",
            "sent_at": "2024-01-15T12:00:00Z",
            "task_id": "abc-123-def",
            "idempotency_key": "memo_1_1_2024-01-15"
        }
    },

    # ========================================================================
    # PORTFOLIO
    # ========================================================================
    "portfolio_stats_response": {
        "summary": "Portfolio Statistics",
        "value": {
            "total_properties": 150,
            "by_stage": {
                "new": 20,
                "outreach": 45,
                "qualified": 30,
                "negotiation": 25,
                "under_contract": 15,
                "closed_won": 10,
                "closed_lost": 5
            },
            "avg_bird_dog_score": 0.73,
            "total_estimated_value": 125000000,
            "conversion_rate": 0.067,
            "avg_days_in_pipeline": 45,
            "this_month": {
                "new_properties": 12,
                "closed_won": 2,
                "closed_lost": 1
            }
        }
    },
    "reconciliation_request": {
        "summary": "Run Portfolio Reconciliation",
        "description": "Validate portfolio data integrity with ±0.5% threshold",
        "value": {
            "portfolio_id": 1
        }
    },
    "reconciliation_response": {
        "summary": "Reconciliation Results",
        "value": {
            "portfolio_id": 1,
            "validation_status": "pass",
            "discrepancy_percentage": 0.23,
            "threshold": 0.5,
            "properties_checked": 150,
            "properties_with_issues": 0,
            "total_value_expected": 125000000,
            "total_value_actual": 125287500,
            "discrepancy_amount": 287500,
            "checked_at": "2024-01-15T14:00:00Z"
        }
    },

    # ========================================================================
    # WEBHOOKS
    # ========================================================================
    "webhook_email_delivered": {
        "summary": "SendGrid Email Delivered",
        "description": "Webhook payload when email is delivered",
        "value": {
            "event": "delivered",
            "email": "jane@example.com",
            "timestamp": 1705323600,
            "smtp-id": "<abc123@sendgrid.net>",
            "sg_event_id": "sendgrid_event_123",
            "sg_message_id": "message_456",
            "communication_id": "1"
            }
    },
    "webhook_email_opened": {
        "summary": "SendGrid Email Opened",
        "value": {
            "event": "open",
            "email": "jane@example.com",
            "timestamp": 1705324200,
            "sg_event_id": "sendgrid_event_124",
            "sg_message_id": "message_456",
            "communication_id": "1",
            "useragent": "Mozilla/5.0..."
        }
    },
    "webhook_sms_delivered": {
        "summary": "Twilio SMS Delivered",
        "value": {
            "MessageSid": "SM1234567890",
            "MessageStatus": "delivered",
            "To": "+15550100",
            "From": "+15550199",
            "Body": "Hi Jane, quick question about...",
            "communication_id": "2"
        }
    },

    # ========================================================================
    # SSE (SERVER-SENT EVENTS)
    # ========================================================================
    "sse_token_response": {
        "summary": "SSE Authentication Token",
        "value": {
            "sse_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "stream_url": "http://localhost:8000/api/v1/sse/stream?token=...",
            "expires_in": 3600
        }
    },
    "sse_event_property_updated": {
        "summary": "SSE: Property Updated",
        "description": "Real-time event when property is updated",
        "value": {
            "event": "property_updated",
            "data": {
                "property_id": 1,
                "team_id": 1,
                "current_stage": "qualified",
                "updated_by": 1,
                "updated_at": "2024-01-15T15:30:00Z"
            }
        }
    },
    "sse_event_memo_generated": {
        "summary": "SSE: Memo Generated",
        "value": {
            "event": "memo_generated",
            "data": {
                "communication_id": 1,
                "property_id": 1,
                "team_id": 1,
                "status": "sent",
                "generated_at": "2024-01-15T12:00:00Z"
            }
        }
    },

    # ========================================================================
    # ADMIN / DLQ
    # ========================================================================
    "dlq_stats_response": {
        "summary": "DLQ Statistics",
        "value": {
            "total_failed": 5,
            "failed_by_queue": {
                "memos": 2,
                "emails": 3,
                "enrichment": 0
            },
            "failed_by_task": {
                "generate_memo": 2,
                "send_email": 3
            },
            "oldest_failure": "2024-01-15T10:00:00Z",
            "alert_status": {
                "should_alert": True,
                "reason": "DLQ depth > 0 for > 5 minutes"
            }
        }
    },
    "dlq_task_detail": {
        "summary": "Failed Task Details",
        "value": {
            "id": 1,
            "task_id": "abc-123-def",
            "task_name": "api.tasks.generate_memo",
            "queue_name": "memos",
            "args": [],
            "kwargs": {
                "property_id": 1,
                "template_id": 1
            },
            "exception_type": "ConnectionError",
            "exception_message": "Failed to connect to LLM API",
            "traceback": "Traceback (most recent call last):\\n  File...",
            "retries_attempted": 3,
            "failed_at": "2024-01-15T10:00:00Z",
            "status": "failed"
        }
    },
    "dlq_replay_request": {
        "summary": "Replay Single Task",
        "value": {
            "task_id": 1,
            "force": False
        }
    },
    "dlq_replay_response": {
        "summary": "Replay Initiated",
        "value": {
            "success": True,
            "replayed_task_id": "def-456-ghi",
            "message": "Task queued for replay"
        }
    },
    "dlq_bulk_replay_request": {
        "summary": "Bulk Replay by Queue",
        "value": {
            "queue": "memos",
            "max_tasks": 100,
            "dry_run": False
        }
    },

    # ========================================================================
    # RATE LIMITING
    # ========================================================================
    "rate_limit_error": {
        "summary": "Rate Limit Exceeded",
        "description": "Response when API rate limit is exceeded",
        "value": {
            "detail": "Rate limit exceeded. Please try again later.",
            "retry_after": 60,
            "limit": 100,
            "remaining": 0,
            "reset_at": "2024-01-15T16:00:00Z"
        }
    },

    # ========================================================================
    # ERRORS
    # ========================================================================
    "error_400": {
        "summary": "Bad Request",
        "value": {
            "detail": "Invalid input data",
            "errors": [
                {
                    "loc": ["body", "email"],
                    "msg": "value is not a valid email address",
                    "type": "value_error.email"
                }
            ]
        }
    },
    "error_401": {
        "summary": "Unauthorized",
        "value": {
            "detail": "Invalid or expired token"
        }
    },
    "error_403": {
        "summary": "Forbidden",
        "value": {
            "detail": "Insufficient permissions"
        }
    },
    "error_404": {
        "summary": "Not Found",
        "value": {
            "detail": "Property not found"
        }
    },
    "error_422": {
        "summary": "Validation Error",
        "value": {
            "detail": [
                {
                    "loc": ["body", "property_id"],
                    "msg": "field required",
                    "type": "value_error.missing"
                }
            ]
        }
    },
    "error_429": {
        "summary": "Too Many Requests",
        "value": {
            "detail": "Rate limit exceeded",
            "retry_after": 60
        }
    },
    "error_500": {
        "summary": "Internal Server Error",
        "value": {
            "detail": "An unexpected error occurred"
        }
    }
}

# ============================================================================
# OPENAPI TAGS METADATA
# ============================================================================

OPENAPI_TAGS = [
    {
        "name": "System",
        "description": "System health checks and status endpoints"
    },
    {
        "name": "Authentication",
        "description": """
User authentication and authorization.

**Features:**
- JWT-based authentication
- Team-based multi-tenancy
- Login attempt tracking and lockout
- Secure password hashing with bcrypt
        """
    },
    {
        "name": "Properties",
        "description": """
Property management and pipeline operations.

**Features:**
- CRUD operations for properties
- Advanced filtering and search
- Pipeline stage management
- Timeline tracking
- ETag support for caching
        """
    },
    {
        "name": "Quick Wins",
        "description": """
Month 1 quick win features for immediate value.

**Features:**
- Generate & Send Combo (AI-powered memo generation)
- Auto-Assign on Reply (automatic lead assignment)
- Stage-Aware Templates (context-specific messaging)
- Flag Data Issue (data quality reporting)
        """
    },
    {
        "name": "Workflow",
        "description": """
Workflow automation and task management.

**Features:**
- Next Best Action (NBA) recommendations
- Smart Lists (saved queries with filters)
- One-Click Tasking (bulk operations)
        """
    },
    {
        "name": "Communications",
        "description": """
Communication management and email/SMS threading.

**Features:**
- Email threading (Gmail/Outlook integration)
- Call capture and transcription
- Reply drafting with AI assistance
- Objection handling suggestions
        """
    },
    {
        "name": "Portfolio",
        "description": """
Portfolio analytics and deal economics.

**Features:**
- Portfolio reconciliation (±0.5% validation)
- Deal economics panel
- Investor readiness score
- Template performance leaderboards
        """
    },
    {
        "name": "Sharing",
        "description": """
Secure sharing and collaboration features.

**Features:**
- Password-free share links
- Deal room artifacts
- Offer pack export
- Access tracking
        """
    },
    {
        "name": "Data & Propensity",
        "description": """
Data enrichment and propensity scoring.

**Features:**
- Owner propensity signals
- Data provenance inspector
- Deliverability dashboard
- Third-party data integration
        """
    },
    {
        "name": "Automation",
        "description": """
Automation rules and operational guardrails.

**Features:**
- Cadence governor (contact frequency limits)
- Compliance pack (DNC, opt-outs, CAN-SPAM)
- Budget tracking and alerts
        """
    },
    {
        "name": "Webhooks",
        "description": """
Webhook handlers for external service events.

**Features:**
- SendGrid email events (delivered, opened, clicked, bounced)
- Twilio SMS events (sent, delivered, failed)
- HMAC signature verification
- Idempotent event processing
        """
    },
    {
        "name": "Jobs",
        "description": """
Background job monitoring and management.

**Features:**
- Celery task status checking
- Job queue inspection
- Task cancellation
        """
    },
    {
        "name": "SSE",
        "description": """
Server-Sent Events for real-time updates.

**Features:**
- JWT-based SSE authentication
- Team-scoped event streams
- Property updates (stage changes, assignments)
- Communication events (memo sent, reply received)
- Two-tab synchronization
        """
    },
    {
        "name": "Admin",
        "description": """
Administrative and monitoring endpoints.

**Features:**
- DLQ (Dead Letter Queue) monitoring
- Task replay (single and bulk)
- System health metrics
- Provider status
        """
    }
]

# ============================================================================
# ENHANCED OPENAPI SCHEMA
# ============================================================================

def get_openapi_schema_enhancements() -> Dict[str, Any]:
    """
    Returns OpenAPI schema enhancements to be merged with FastAPI's auto-generated schema
    """
    return {
        "info": {
            "title": "Real Estate OS API",
            "version": "1.0.0",
            "description": """
# Real Estate OS - Complete UX Platform API

**Decision speed, not just data** - Surface the one thing to do next for each deal, with context.

## Quick Start

1. **Register** a new account at `POST /api/v1/auth/register`
2. **Login** to get an access token at `POST /api/v1/auth/login`
3. **Create properties** at `POST /api/v1/properties`
4. **Generate memos** at `POST /api/v1/quick-wins/generate-and-send`

## Authentication

All endpoints (except `/auth/register` and `/auth/login`) require JWT authentication:

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
  https://api.realestateos.com/api/v1/properties
```

Tokens expire after 24 hours. Refresh by logging in again.

## Rate Limiting

API requests are rate-limited to prevent abuse:
- **100 requests per minute** per user
- **1000 requests per hour** per team

Rate limit information is included in response headers:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Unix timestamp when limit resets

## Idempotency

Critical endpoints support idempotency to prevent duplicate operations:
- Include `Idempotency-Key` header with a unique value
- Same key returns cached response for 24 hours
- Memo generation automatically uses: `memo_{property_id}_{template_id}_{date}`

Example:
```bash
curl -X POST -H "Idempotency-Key: memo_123_1_2024-01-15" \\
  https://api.realestateos.com/api/v1/quick-wins/generate-and-send
```

## Webhooks

Register webhook URLs to receive real-time events:
- **SendGrid**: Email delivery events (delivered, opened, clicked)
- **Twilio**: SMS delivery events (sent, delivered, failed)

All webhooks verify HMAC signatures for security.

## Real-Time Updates (SSE)

Subscribe to Server-Sent Events for live updates:
1. Get SSE token: `POST /api/v1/sse/token`
2. Connect to stream: `GET /api/v1/sse/stream?token=TOKEN`
3. Receive events: property updates, memo generation, replies

## Error Handling

API uses standard HTTP status codes:
- `200`: Success
- `201`: Created
- `400`: Bad Request (invalid input)
- `401`: Unauthorized (missing/invalid token)
- `403`: Forbidden (insufficient permissions)
- `404`: Not Found
- `422`: Validation Error
- `429`: Rate Limit Exceeded
- `500`: Internal Server Error

All errors return JSON with `detail` field explaining the issue.

## Pagination

List endpoints support pagination:
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum records to return (default: 100, max: 1000)

Example:
```bash
GET /api/v1/properties?skip=100&limit=50
```

## Caching & ETags

GET endpoints support conditional requests with ETags:
- Include `If-None-Match` header with previous ETag
- Receive `304 Not Modified` if content unchanged
- Saves bandwidth and improves performance

## Monitoring

- **Health Check**: `GET /healthz`
- **Metrics**: `GET /metrics` (Prometheus format)
- **API Status**: `GET /api/v1/status`

## Support

- Documentation: https://docs.realestateos.com
- Support: support@realestateos.com
- Status Page: https://status.realestateos.com
            """,
            "contact": {
                "name": "Real Estate OS Support",
                "email": "support@realestateos.com",
                "url": "https://realestateos.com/support"
            },
            "license": {
                "name": "Proprietary",
                "url": "https://realestateos.com/license"
            },
            "termsOfService": "https://realestateos.com/terms"
        },
        "servers": [
            {
                "url": "https://api.realestateos.com",
                "description": "Production"
            },
            {
                "url": "https://staging-api.realestateos.com",
                "description": "Staging"
            },
            {
                "url": "http://localhost:8000",
                "description": "Local Development"
            }
        ],
        "externalDocs": {
            "description": "Complete Documentation",
            "url": "https://docs.realestateos.com"
        },
        "tags": OPENAPI_TAGS,
        "x-tagGroups": [
            {
                "name": "Core Features",
                "tags": ["Authentication", "Properties", "Communications"]
            },
            {
                "name": "Quick Wins",
                "tags": ["Quick Wins", "Workflow"]
            },
            {
                "name": "Advanced Features",
                "tags": ["Portfolio", "Sharing", "Data & Propensity", "Automation"]
            },
            {
                "name": "Integration",
                "tags": ["Webhooks", "Jobs", "SSE"]
            },
            {
                "name": "System",
                "tags": ["System", "Admin"]
            }
        ]
    }
