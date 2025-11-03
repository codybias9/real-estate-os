# Dead Letter Queue (DLQ) System

## Overview

The DLQ system provides comprehensive failed task management for Celery background jobs with replay capabilities, monitoring, and alerting.

## Features

✅ **Automatic Failure Tracking**: All failed Celery tasks are automatically recorded to database
✅ **RabbitMQ DLX Integration**: Uses Dead Letter Exchange for queue-level DLQ routing
✅ **Admin Replay Endpoints**: Auth-gated REST API for task inspection and replay
✅ **Idempotency on Replay**: Prevents duplicate side-effects when replaying tasks
✅ **Progressive Monitoring**: Alerts when DLQ depth > 0 for > 5 minutes
✅ **Bulk Operations**: Replay multiple tasks with filtering and limits
✅ **Archive Support**: Mark tasks as resolved without replay

## Architecture

### DLQ Flow

```
┌─────────────────┐
│  Celery Task    │
│  Fails (3x)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  RabbitMQ DLX   │  ← Dead Letter Exchange
│  Routes to DLQ  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ DLQTask.on_fail │  ← Automatic recording
│ Records to DB   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ failed_tasks    │  ← PostgreSQL table
│ table           │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Admin API       │  ← /admin/dlq/* endpoints
│ Inspect/Replay  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Monitoring      │  ← Periodic checks (5 min)
│ & Alerts        │
└─────────────────┘
```

### Components

1. **RabbitMQ DLX Configuration** (`api/celery_app.py`)
   - Queue-specific Dead Letter Exchange setup
   - 24-hour TTL for messages
   - Automatic routing to `dlx` exchange

2. **DLQ Task Base Class** (`api/dlq.py`)
   - Extends Celery `Task` class
   - Automatic failure recording in `on_failure()` hook
   - Stores: task_id, args, kwargs, exception, traceback

3. **Failed Tasks Table** (`db/models.py`, `db/migrations/versions/004_add_dlq_tracking.py`)
   - Tracks all failed tasks with full context
   - Supports replay tracking (status, replay_count)
   - Indexed for efficient queries

4. **Admin Endpoints** (`api/routers/admin.py`)
   - Auth-gated (ADMIN role required)
   - REST API for DLQ management
   - Rate limited to prevent abuse

5. **Monitoring Tasks** (`api/tasks/maintenance_tasks.py`)
   - Periodic DLQ alert checks (every 5 minutes)
   - Idempotency key cleanup (daily)

## Database Schema

### `failed_tasks` Table

```sql
CREATE TABLE failed_tasks (
    id SERIAL PRIMARY KEY,

    -- Task identification
    task_id VARCHAR(255) NOT NULL UNIQUE,  -- Original Celery task ID
    task_name VARCHAR(255) NOT NULL,       -- e.g., "api.tasks.memo_tasks.generate_memo_async"
    queue_name VARCHAR(100) NOT NULL DEFAULT 'default',

    -- Task arguments (for replay)
    args JSONB NOT NULL DEFAULT '[]',
    kwargs JSONB NOT NULL DEFAULT '{}',

    -- Failure details
    exception_type VARCHAR(255),
    exception_message TEXT,
    traceback TEXT,
    retries_attempted INTEGER NOT NULL DEFAULT 0,

    -- Timestamps
    failed_at TIMESTAMP NOT NULL DEFAULT now(),
    replayed_at TIMESTAMP,

    -- Replay tracking
    status VARCHAR(50) NOT NULL DEFAULT 'failed',  -- failed, replaying, replayed, archived
    replayed_task_id VARCHAR(255),                 -- New task ID if replayed
    replay_count INTEGER NOT NULL DEFAULT 0
);

-- Indexes for efficient queries
CREATE INDEX idx_failedtask_status ON failed_tasks(status);
CREATE INDEX idx_failedtask_queue ON failed_tasks(queue_name);
CREATE INDEX idx_failedtask_task_name ON failed_tasks(task_name);
CREATE INDEX idx_failedtask_failed_at ON failed_tasks(failed_at);
```

## API Reference

### Admin Endpoints

All endpoints require **ADMIN role** authentication.

#### GET /api/v1/admin/dlq/stats

Get DLQ statistics and monitoring data.

**Response:**
```json
{
  "total_failed": 5,
  "by_queue": {
    "memos": 3,
    "emails": 2
  },
  "by_status": {
    "failed": 4,
    "replaying": 1
  },
  "oldest_failure": "2025-01-15T10:30:00",
  "time_since_oldest_minutes": 15.5,
  "alert_threshold_exceeded": true,
  "alert_message": "DLQ has 5 failed tasks for 15 minutes"
}
```

#### GET /api/v1/admin/dlq/tasks

List failed tasks with filtering and pagination.

**Query Parameters:**
- `queue_name` (optional): Filter by queue
- `status` (optional): Filter by status (failed, replaying, replayed, archived)
- `limit` (default: 100, max: 1000): Max results
- `offset` (default: 0): Pagination offset

**Response:**
```json
[
  {
    "id": 1,
    "task_id": "abc-123-def-456",
    "task_name": "api.tasks.memo_tasks.generate_memo_async",
    "queue_name": "memos",
    "args": [123],
    "kwargs": {"template": "default"},
    "exception_type": "ValueError",
    "exception_message": "Property not found",
    "traceback": "Traceback (most recent call last)...",
    "retries_attempted": 3,
    "failed_at": "2025-01-15T10:30:00",
    "replayed_at": null,
    "status": "failed",
    "replay_count": 0
  }
]
```

#### GET /api/v1/admin/dlq/tasks/{failed_task_id}

Get detailed information about a specific failed task.

**Response:** Same as individual task in list above.

#### POST /api/v1/admin/dlq/replay

Replay a single failed task.

**Request Body:**
```json
{
  "failed_task_id": 1,
  "force": false  // Force replay even if already replayed
}
```

**Response:**
```json
{
  "success": true,
  "failed_task_id": 1,
  "original_task_id": "abc-123-def-456",
  "new_task_id": "xyz-789-ghi-012",
  "task_name": "api.tasks.memo_tasks.generate_memo_async",
  "replay_count": 1,
  "message": "Task replayed successfully with ID xyz-789-ghi-012"
}
```

#### POST /api/v1/admin/dlq/replay-bulk

Replay multiple failed tasks in bulk.

**Request Body:**
```json
{
  "queue_name": "memos",           // Optional: filter by queue
  "task_name": "api.tasks.memo_tasks.generate_memo_async",  // Optional
  "failed_after": "2025-01-15T00:00:00",  // Optional
  "limit": 100                     // Max tasks to replay
}
```

**Response:**
```json
{
  "total_attempted": 10,
  "successful": 9,
  "failed": 1,
  "results": [
    {
      "success": true,
      "failed_task_id": 1,
      "new_task_id": "xyz-789",
      "message": "Task replayed successfully"
    },
    // ... more results
  ]
}
```

#### POST /api/v1/admin/dlq/archive/{failed_task_id}

Archive a failed task without replay (marks as resolved).

**Use Cases:**
- Task is no longer relevant
- Issue was resolved manually
- Task should not be replayed

**Response:**
```json
{
  "success": true,
  "message": "Task 1 archived successfully"
}
```

#### GET /api/v1/admin/dlq/alerts

Check if DLQ alerts should fire.

**Alert Conditions:**
- DLQ depth > 0 for > 5 minutes
- Alert clears when DLQ is empty or all tasks replayed

**Response (Alert Active):**
```json
{
  "alert": true,
  "severity": "warning",
  "title": "DLQ Has Failed Tasks",
  "message": "DLQ has 5 failed tasks for 15 minutes",
  "total_failed": 5,
  "oldest_failure": "2025-01-15T10:30:00",
  "time_since_oldest_minutes": 15.5,
  "by_queue": {
    "memos": 3,
    "emails": 2
  },
  "recommended_action": "Review failed tasks and replay or archive them"
}
```

**Response (No Alert):**
```json
{
  "alert": false,
  "message": "DLQ is healthy - no alerts"
}
```

#### GET /api/v1/admin/health/detailed

Detailed system health check including DLQ status.

**Response:**
```json
{
  "timestamp": "2025-01-15T12:00:00",
  "database": "healthy",
  "redis": "healthy",
  "cache": "healthy",
  "dlq": {
    "status": "healthy",  // or "alert"
    "failed_tasks": 0,
    "oldest_failure": null
  }
}
```

## Usage Examples

### Using Python SDK

```python
import requests

# Admin authentication
headers = {
    "Authorization": "Bearer <admin_token>"
}

# Get DLQ statistics
response = requests.get(
    "https://api.real-estate-os.com/api/v1/admin/dlq/stats",
    headers=headers
)
stats = response.json()
print(f"Failed tasks: {stats['total_failed']}")

# List failed tasks
response = requests.get(
    "https://api.real-estate-os.com/api/v1/admin/dlq/tasks",
    params={"queue_name": "memos", "status": "failed"},
    headers=headers
)
failed_tasks = response.json()

# Replay a specific task
response = requests.post(
    "https://api.real-estate-os.com/api/v1/admin/dlq/replay",
    json={"failed_task_id": 1, "force": False},
    headers=headers
)
result = response.json()
print(f"New task ID: {result['new_task_id']}")

# Bulk replay all failed memo tasks
response = requests.post(
    "https://api.real-estate-os.com/api/v1/admin/dlq/replay-bulk",
    json={
        "queue_name": "memos",
        "status": "failed",
        "limit": 50
    },
    headers=headers
)
result = response.json()
print(f"Replayed {result['successful']} tasks")
```

### Using cURL

```bash
# Get DLQ stats
curl -X GET https://api.real-estate-os.com/api/v1/admin/dlq/stats \
  -H "Authorization: Bearer <admin_token>"

# Replay a task
curl -X POST https://api.real-estate-os.com/api/v1/admin/dlq/replay \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"failed_task_id": 1, "force": false}'

# Check alerts
curl -X GET https://api.real-estate-os.com/api/v1/admin/dlq/alerts \
  -H "Authorization: Bearer <admin_token>"
```

## Monitoring & Alerting

### Periodic Tasks

The system runs two periodic Celery Beat tasks:

1. **DLQ Alert Check** (every 5 minutes)
   - Task: `api.tasks.maintenance_tasks.check_dlq_alerts`
   - Checks if DLQ depth > 0 for > 5 minutes
   - Logs warnings with structured data
   - TODO: Integrate with Slack/PagerDuty/email

2. **Idempotency Key Cleanup** (daily at 4:00 AM)
   - Task: `api.tasks.maintenance_tasks.cleanup_idempotency_keys`
   - Removes expired idempotency keys (TTL: 24 hours)
   - Prevents database bloat

### Grafana Integration

Create dashboard panels using the DLQ API:

```promql
# DLQ depth gauge
dlq_total_failed{job="real-estate-os-api"}

# Failed tasks by queue
dlq_failed_by_queue{job="real-estate-os-api", queue="memos"}

# Time since oldest failure
dlq_time_since_oldest_minutes{job="real-estate-os-api"}

# Alert: DLQ depth > 0 for > 5 minutes
ALERTS{alertname="DLQDepthExceeded", severity="warning"}
```

### Alert Rules

**Prometheus AlertManager:**

```yaml
groups:
  - name: dlq_alerts
    interval: 1m
    rules:
      - alert: DLQDepthExceeded
        expr: dlq_time_since_oldest_minutes > 5 AND dlq_total_failed > 0
        for: 5m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "DLQ has {{ $value }} failed tasks for > 5 minutes"
          description: "Review failed tasks at https://app.real-estate-os.com/admin/dlq"
          runbook: "https://docs.real-estate-os.com/runbooks/dlq-replay"
```

## Idempotency on Replay

All task replays maintain idempotency to prevent duplicate side-effects:

### How It Works

1. **Original Task Execution**
   - Task includes idempotency key (header or generated)
   - Operation completes and stores response in `idempotency_keys` table
   - Task fails after storing response

2. **Task Replay**
   - Admin replays task with same args/kwargs
   - Idempotency handler checks for existing key
   - **Cached response returned** instead of re-executing operation
   - No duplicate side-effects (emails, payments, etc.)

### Example

```python
# Original task (fails after sending email)
@celery_app.task
def send_email_task(property_id, template):
    # Idempotency key: "send_email:123:welcome"
    idempotency_key = f"send_email:{property_id}:{template}"

    # Check for existing
    existing = check_idempotency(idempotency_key)
    if existing:
        return existing  # Return cached result

    # Send email (side-effect)
    result = send_email(property_id, template)

    # Store result with idempotency key
    store_idempotency(idempotency_key, result)

    # Task fails here (e.g., network error)
    raise Exception("Network error")

# Replay (idempotency prevents duplicate email)
replay_failed_task(task_id=123)  # Returns cached result, no email sent
```

## Operational Runbook

### When DLQ Alert Fires

1. **Investigate Root Cause**
   ```bash
   # Check DLQ stats
   curl -X GET /api/v1/admin/dlq/stats -H "Authorization: Bearer $TOKEN"

   # Get failed task details
   curl -X GET /api/v1/admin/dlq/tasks?status=failed -H "Authorization: Bearer $TOKEN"
   ```

2. **Review Failure Details**
   - Check `exception_type` and `exception_message`
   - Review `traceback` for debugging
   - Check `queue_name` to identify affected system

3. **Determine Action**
   - **Transient Failure** (network, timeout): Replay task
   - **Data Issue** (missing property, invalid input): Fix data, then replay
   - **Code Bug** (logic error): Deploy fix, then replay
   - **No Longer Relevant**: Archive task

4. **Replay or Archive**
   ```bash
   # Replay single task
   curl -X POST /api/v1/admin/dlq/replay \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"failed_task_id": 1}'

   # Bulk replay (after fix deployed)
   curl -X POST /api/v1/admin/dlq/replay-bulk \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"queue_name": "memos", "limit": 100}'

   # Archive if not relevant
   curl -X POST /api/v1/admin/dlq/archive/1 \
     -H "Authorization: Bearer $TOKEN"
   ```

5. **Verify Resolution**
   ```bash
   # Check stats again
   curl -X GET /api/v1/admin/dlq/stats -H "Authorization: Bearer $TOKEN"

   # Alert should clear when DLQ is empty
   ```

### Preventive Measures

1. **Monitor DLQ Dashboard**: Weekly review of failure patterns
2. **Improve Retry Logic**: Adjust `task_max_retries` for transient failures
3. **Add Circuit Breakers**: Fail fast on known outages
4. **Enhance Input Validation**: Catch errors before task execution
5. **Set Up Alerts**: Slack/PagerDuty integration for critical failures

## Configuration

### Environment Variables

```bash
# Celery Broker (RabbitMQ with DLX support)
CELERY_BROKER_URL=amqp://admin:admin@localhost:5672/

# Celery Result Backend (Redis)
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Database (PostgreSQL)
DB_DSN=postgresql://user:pass@localhost:5432/real_estate_os
```

### RabbitMQ Setup

Ensure RabbitMQ has Dead Letter Exchange configured:

```bash
# Declare Dead Letter Exchange
rabbitmqadmin declare exchange name=dlx type=topic durable=true

# Declare DLQ queues
rabbitmqadmin declare queue name=dlq.memos durable=true
rabbitmqadmin declare queue name=dlq.enrichment durable=true
rabbitmqadmin declare queue name=dlq.emails durable=true
rabbitmqadmin declare queue name=dlq.maintenance durable=true

# Bind DLQ queues to DLX
rabbitmqadmin declare binding source=dlx destination=dlq.memos routing_key=dlq.memos
rabbitmqadmin declare binding source=dlx destination=dlq.enrichment routing_key=dlq.enrichment
rabbitmqadmin declare binding source=dlx destination=dlq.emails routing_key=dlq.emails
rabbitmqadmin declare binding source=dlx destination=dlq.maintenance routing_key=dlq.maintenance
```

## Testing

### Unit Tests

```python
def test_record_failed_task(db_session):
    """Test recording a failed task"""
    from api.dlq import record_failed_task

    task_id = record_failed_task(
        db=db_session,
        task_id="test-123",
        task_name="api.tasks.memo_tasks.generate_memo_async",
        args=[123],
        kwargs={"template": "default"},
        exception=ValueError("Test error"),
        traceback="Traceback...",
        queue_name="memos",
        retries=3
    )

    assert task_id is not None

    # Verify record exists
    from db.models import FailedTask
    task = db_session.query(FailedTask).filter(FailedTask.task_id == "test-123").first()
    assert task is not None
    assert task.status == "failed"
    assert task.retries_attempted == 3


def test_replay_failed_task(db_session):
    """Test replaying a failed task"""
    from api.dlq import replay_failed_task, record_failed_task

    # Record a failed task
    task_id = record_failed_task(
        db=db_session,
        task_id="test-456",
        task_name="api.tasks.memo_tasks.generate_memo_async",
        args=[123],
        kwargs={"template": "default"},
        exception=ValueError("Test error"),
        traceback="Traceback...",
        queue_name="memos",
        retries=3
    )

    # Replay the task
    result = replay_failed_task(db_session, task_id)

    assert result["success"] is True
    assert result["new_task_id"] is not None

    # Verify status updated
    from db.models import FailedTask
    task = db_session.query(FailedTask).filter(FailedTask.id == task_id).first()
    assert task.status == "replayed"
    assert task.replay_count == 1


def test_dlq_alert_threshold(db_session):
    """Test DLQ alert threshold logic"""
    from api.dlq import check_dlq_alerts
    from datetime import datetime, timedelta

    # Create old failed task (> 5 minutes)
    record_failed_task(
        db=db_session,
        task_id="test-old",
        task_name="api.tasks.memo_tasks.generate_memo_async",
        args=[123],
        kwargs={},
        exception=ValueError("Test"),
        traceback="Traceback...",
        queue_name="memos",
        retries=3
    )

    # Manually set failed_at to 10 minutes ago
    from db.models import FailedTask
    task = db_session.query(FailedTask).filter(FailedTask.task_id == "test-old").first()
    task.failed_at = datetime.utcnow() - timedelta(minutes=10)
    db_session.commit()

    # Check alerts
    alert = check_dlq_alerts(db_session)

    assert alert is not None
    assert alert["alert"] is True
    assert alert["alert_threshold_exceeded"] is True
    assert alert["total_failed"] >= 1
```

## Security Considerations

1. **Admin-Only Access**
   - All DLQ endpoints require ADMIN role
   - Auth token verification on every request
   - Rate limited to prevent abuse

2. **Audit Logging**
   - All replay operations logged
   - Includes admin user ID and timestamp
   - Traceable for compliance

3. **Data Sensitivity**
   - Failed task args/kwargs may contain PII
   - Restrict access to authorized personnel
   - Consider encrypting sensitive fields

4. **Replay Safety**
   - Idempotency prevents duplicate side-effects
   - No financial operations replayed without verification
   - Archive option for tasks that shouldn't be replayed

## Troubleshooting

### DLQ Not Recording Failures

**Symptom**: Tasks fail but don't appear in `failed_tasks` table.

**Solutions:**
1. Check Celery is using `DLQTask` base class:
   ```python
   # In api/celery_app.py
   from api.dlq import DLQTask
   celery_app.Task = DLQTask
   ```

2. Verify database connection in task context:
   ```python
   # Check SessionLocal is accessible
   from api.database import SessionLocal
   ```

3. Check logs for database errors:
   ```bash
   grep "Failed to record failed task" celery.log
   ```

### Replay Not Working

**Symptom**: Replay endpoint returns success but task doesn't execute.

**Solutions:**
1. Verify Celery workers are running:
   ```bash
   celery -A api.celery_app inspect active
   ```

2. Check task is registered:
   ```python
   from api.celery_app import celery_app
   print(celery_app.tasks.keys())
   ```

3. Review replay logs:
   ```bash
   grep "Replaying task" celery.log
   ```

### Alert Not Firing

**Symptom**: DLQ has failed tasks but no alerts.

**Solutions:**
1. Verify Celery Beat is running:
   ```bash
   celery -A api.celery_app beat --loglevel=info
   ```

2. Check beat schedule:
   ```python
   from api.celery_app import celery_app
   print(celery_app.conf.beat_schedule)
   ```

3. Manually trigger alert check:
   ```bash
   celery -A api.celery_app call api.tasks.maintenance_tasks.check_dlq_alerts
   ```

## Future Enhancements

- [ ] Grafana dashboard with DLQ metrics
- [ ] Slack/PagerDuty integration for alerts
- [ ] Auto-replay with configurable policies
- [ ] Machine learning for failure pattern detection
- [ ] Dead task archival after 30 days
- [ ] Replay rate limiting (avoid overwhelming workers)
- [ ] Failed task categorization (transient, permanent, unknown)
- [ ] Replay scheduling (replay at specific time)
- [ ] Replay approval workflow (require 2nd admin approval)
