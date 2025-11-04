# Dead Letter Queue (DLQ) Replay Runbook

## Overview

This runbook provides step-by-step instructions for monitoring, investigating, and replaying failed Celery tasks from the Dead Letter Queue (DLQ).

**Audience**: DevOps Engineers, Backend Developers, On-Call Engineers
**Prerequisites**: API access, database access, Celery/RabbitMQ access
**Estimated Time**: 15-45 minutes (depends on failure count)
**Risk Level**: Medium - replay may cause duplicate operations if not idempotent

---

## Table of Contents

1. [Understanding the DLQ](#understanding-the-dlq)
2. [Monitoring and Alerts](#monitoring-and-alerts)
3. [Investigation Process](#investigation-process)
4. [Replay Procedures](#replay-procedures)
5. [Bulk Operations](#bulk-operations)
6. [Troubleshooting](#troubleshooting)
7. [Prevention](#prevention)

---

## Understanding the DLQ

### What is the DLQ?

The Dead Letter Queue captures Celery tasks that failed after maximum retry attempts. Failed tasks are automatically recorded to the `failed_tasks` table for investigation and replay.

### How Tasks Reach the DLQ

1. Task executes and raises an exception
2. Celery retries according to task configuration (default: 3 retries)
3. After max retries exhausted, task fails permanently
4. Our custom `DLQTask` base class captures failure
5. Failure details stored in database
6. RabbitMQ DLX (Dead Letter Exchange) routes message

### DLQ Workflow

```
[Task Execution] → [Exception] → [Retry 1] → [Retry 2] → [Retry 3] →
[Max Retries Reached] → [DLQ Recording] → [Manual Intervention]
```

---

## Monitoring and Alerts

### Dashboard Access

```bash
# View DLQ stats via API
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  https://api.realestateos.com/api/v1/admin/dlq/stats

# Example response:
# {
#   "total_failed": 42,
#   "failed_by_queue": {
#     "memos": 15,
#     "emails": 20,
#     "enrichment": 7
#   },
#   "failed_by_task": {
#     "generate_memo": 15,
#     "send_email": 20,
#     "enrich_property": 7
#   },
#   "oldest_failure": "2024-01-15T10:30:00Z",
#   "alert_status": {
#     "should_alert": true,
#     "reason": "DLQ depth > 0 for > 5 minutes"
#   }
# }
```

### Alert Conditions

**Primary Alert**: DLQ depth > 0 for > 5 minutes

```bash
# Check if alert should trigger
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  https://api.realestateos.com/api/v1/admin/dlq/alerts
```

**Alert Channels**:
- PagerDuty: High-priority failures
- Slack: #ops-alerts channel
- Email: ops-team@example.com

### Metrics to Monitor

1. **Total Failed Tasks**: Should be 0 in healthy system
2. **Failure Rate**: Failures per hour/day
3. **Queue Distribution**: Which queues are failing most
4. **Task Types**: Which tasks are failing most
5. **Error Types**: Common exception patterns

---

## Investigation Process

### Step 1: Get DLQ Overview

```bash
# List recent failed tasks
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  "https://api.realestateos.com/api/v1/admin/dlq/tasks?limit=50" | jq '.'

# Filter by queue
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  "https://api.realestateos.com/api/v1/admin/dlq/tasks?queue=memos" | jq '.'

# Filter by task name
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  "https://api.realestateos.com/api/v1/admin/dlq/tasks?task_name=generate_memo" | jq '.'

# Filter by status
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  "https://api.realestateos.com/api/v1/admin/dlq/tasks?status=failed" | jq '.'
```

### Step 2: Analyze Failure Patterns

```sql
-- Connect to database
psql -U postgres -d realestateos

-- Get failure summary
SELECT
  task_name,
  exception_type,
  COUNT(*) as failure_count,
  MAX(failed_at) as last_failure
FROM failed_tasks
WHERE status = 'failed'
GROUP BY task_name, exception_type
ORDER BY failure_count DESC;

-- Get error messages
SELECT
  task_name,
  exception_message,
  COUNT(*) as count
FROM failed_tasks
WHERE status = 'failed'
GROUP BY task_name, exception_message
ORDER BY count DESC
LIMIT 20;

-- Find tasks with high retry counts
SELECT
  task_id,
  task_name,
  retries_attempted,
  exception_message,
  failed_at
FROM failed_tasks
WHERE retries_attempted >= 3
ORDER BY failed_at DESC
LIMIT 10;
```

### Step 3: Investigate Individual Failures

```bash
# Get specific task details
TASK_ID="12345"

curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  "https://api.realestateos.com/api/v1/admin/dlq/tasks/$TASK_ID" | jq '.'

# Example response shows:
# - Task arguments
# - Exception type and message
# - Full traceback
# - Retry history
# - Failure timestamp
```

```sql
-- Get task details from database
SELECT
  task_id,
  task_name,
  queue_name,
  args,
  kwargs,
  exception_type,
  exception_message,
  traceback,
  retries_attempted,
  failed_at
FROM failed_tasks
WHERE id = 12345;

-- Get related records
-- For memo generation tasks:
SELECT * FROM properties WHERE id = (
  SELECT (kwargs->>'property_id')::int FROM failed_tasks WHERE id = 12345
);
```

### Step 4: Categorize Failures

**Transient Failures** (Safe to Replay):
- Network timeouts
- Rate limiting (429)
- Temporary service unavailability
- Database connection errors
- Lock timeouts

**Permanent Failures** (Require Fix):
- Invalid data format
- Missing required fields
- Foreign key violations
- Business logic errors
- Invalid API keys

**Data Issues** (Require Manual Fix):
- Deleted referenced records
- Data integrity violations
- Invalid property states

---

## Replay Procedures

### Single Task Replay

**When to use**: Investigating specific failure or testing fix

```bash
# Replay single task
curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.realestateos.com/api/v1/admin/dlq/replay" \
  -d '{
    "task_id": 12345,
    "force": false
  }'

# Response:
# {
#   "success": true,
#   "replayed_task_id": "abc-123-def",
#   "message": "Task queued for replay"
# }

# With force flag (skip duplicate check):
curl -X POST ... -d '{"task_id": 12345, "force": true}'
```

**Monitor replay:**

```bash
# Check task status
celery -A api.celery_app inspect active | grep abc-123-def

# Check logs
docker logs celery-worker-1 | grep abc-123-def

# Verify in database
SELECT status FROM failed_tasks WHERE id = 12345;
# Should show: replayed
```

### Bulk Replay

**When to use**: After fixing underlying issue, replay all affected tasks

#### Replay by Queue

```bash
# Replay all failed tasks in memos queue
curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.realestateos.com/api/v1/admin/dlq/replay-bulk" \
  -d '{
    "queue": "memos",
    "max_tasks": 100,
    "dry_run": true
  }'

# Review dry run output, then execute
curl -X POST ... -d '{
  "queue": "memos",
  "max_tasks": 100,
  "dry_run": false
}'
```

#### Replay by Task Name

```bash
# Replay all generate_memo tasks
curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.realestateos.com/api/v1/admin/dlq/replay-bulk" \
  -d '{
    "task_name": "api.tasks.generate_memo",
    "max_tasks": 50
  }'
```

#### Replay by Time Range

```bash
# Replay tasks that failed in last hour
curl -X POST ... -d '{
  "failed_after": "2024-01-15T14:00:00Z",
  "max_tasks": 100
}'
```

#### Replay by Exception Type

```bash
# Replay all ConnectionError failures
curl -X POST ... -d '{
  "exception_type": "ConnectionError",
  "max_tasks": 200
}'
```

### Selective Replay with SQL

For complex filtering:

```sql
-- Mark tasks for replay
UPDATE failed_tasks
SET status = 'pending_replay'
WHERE exception_type = 'TemporaryError'
  AND failed_at > NOW() - INTERVAL '1 hour'
  AND queue_name = 'memos';

-- Then replay via API
```

---

## Bulk Operations

### Safety Checks Before Bulk Replay

```bash
# 1. Check system health
curl https://api.realestateos.com/health

# 2. Check Celery queue depths
celery -A api.celery_app inspect active_queues

# 3. Check database connections
psql -U postgres -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';"

# 4. Check RabbitMQ status
sudo rabbitmqctl status

# 5. Verify no ongoing deployments
kubectl get pods | grep -v Running
```

### Staged Replay Strategy

For large numbers of failures (> 100):

```bash
# Stage 1: Replay 10 tasks (test)
curl -X POST ... -d '{"max_tasks": 10, "queue": "memos"}'

# Wait 5 minutes, check results
SELECT status, COUNT(*) FROM failed_tasks WHERE replayed_at > NOW() - INTERVAL '5 minutes' GROUP BY status;

# Stage 2: Replay 50 tasks
curl -X POST ... -d '{"max_tasks": 50, "queue": "memos"}'

# Stage 3: Replay remaining
curl -X POST ... -d '{"max_tasks": 1000, "queue": "memos"}'
```

### Rate Limiting Bulk Replay

```python
# Custom script for controlled replay
import requests
import time

ADMIN_TOKEN = "your-token"
HEADERS = {"Authorization": f"Bearer {ADMIN_TOKEN}"}

# Get failed tasks
response = requests.get(
    "https://api.realestateos.com/api/v1/admin/dlq/tasks",
    headers=HEADERS,
    params={"status": "failed", "limit": 500}
)

tasks = response.json()

# Replay in batches with delays
BATCH_SIZE = 10
DELAY_SECONDS = 30

for i in range(0, len(tasks), BATCH_SIZE):
    batch = tasks[i:i+BATCH_SIZE]

    for task in batch:
        requests.post(
            "https://api.realestateos.com/api/v1/admin/dlq/replay",
            headers=HEADERS,
            json={"task_id": task["id"]}
        )

    print(f"Replayed batch {i//BATCH_SIZE + 1}")
    time.sleep(DELAY_SECONDS)
```

---

## Troubleshooting

### Issue: Replay Fails Immediately

**Symptoms**: Replayed task fails again with same error

**Investigation**:
```bash
# Check if underlying issue fixed
curl https://api.realestateos.com/health

# Check external service status
curl https://email-provider.com/status

# Verify API keys/credentials
env | grep API_KEY
```

**Solutions**:
1. Fix root cause before replaying
2. Update task code if business logic changed
3. Clean up invalid data
4. Archive unfixable tasks

### Issue: Duplicate Operations

**Symptoms**: Replayed task creates duplicate records

**Prevention**:
```bash
# Always use idempotency keys
# Check task implementation has idempotency

# For memo generation:
SELECT * FROM communications
WHERE property_id = 123
  AND created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC;

# Should see only one communication per replay
```

**Cleanup**:
```sql
-- Delete duplicates (keep oldest)
DELETE FROM communications
WHERE id IN (
  SELECT id FROM (
    SELECT id, ROW_NUMBER() OVER (
      PARTITION BY property_id, template_id, created_at::date
      ORDER BY id
    ) as rn
    FROM communications
  ) t
  WHERE rn > 1
);
```

### Issue: Tasks Stuck in Replay

**Symptoms**: Replay initiated but tasks never complete

**Investigation**:
```bash
# Check Celery workers
celery -A api.celery_app inspect active

# Check queue depths
celery -A api.celery_app inspect reserved

# Check worker logs
docker logs celery-worker-1 --tail=100
```

**Solutions**:
```bash
# Restart Celery workers
docker-compose restart celery-worker

# Or for Kubernetes
kubectl rollout restart deployment/celery-worker
```

### Issue: High Replay Failure Rate

**Symptoms**: > 50% of replayed tasks fail again

**Actions**:
1. Stop bulk replay immediately
2. Investigate root cause thoroughly
3. Fix underlying issue
4. Test single task replay
5. Resume bulk replay cautiously

---

## Prevention

### Best Practices

1. **Implement Proper Error Handling**
```python
@celery_app.task(bind=True, name="my_task")
def my_task(self):
    try:
        # Task logic
        pass
    except TemporaryError as e:
        # Retry for transient errors
        raise self.retry(exc=e, countdown=60, max_retries=3)
    except PermanentError as e:
        # Don't retry permanent errors
        logger.error(f"Permanent error: {e}")
        raise
```

2. **Use Idempotency Keys**
```python
# All mutations should use idempotency
idempotency_key = f"memo_{property_id}_{template_id}_{date}"
```

3. **Add Circuit Breakers**
```python
if failure_rate > 0.5:
    circuit_breaker.open()
    # Stop processing until issue resolved
```

4. **Monitor Task Success Rates**
```sql
-- Daily task success rate
SELECT
  task_name,
  COUNT(*) FILTER (WHERE status = 'success') as successes,
  COUNT(*) FILTER (WHERE status = 'failed') as failures,
  ROUND(
    COUNT(*) FILTER (WHERE status = 'success')::numeric /
    NULLIF(COUNT(*), 0) * 100,
    2
  ) as success_rate
FROM task_executions
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY task_name;
```

5. **Set Up Alerting**
- Alert when DLQ depth > 0 for > 5 minutes
- Alert when failure rate > 10%
- Alert when specific tasks always fail

### Archive Old Failures

```sql
-- Archive failures older than 30 days
UPDATE failed_tasks
SET status = 'archived'
WHERE failed_at < NOW() - INTERVAL '30 days'
  AND status IN ('failed', 'replayed');
```

### Regular DLQ Review

**Weekly Review Checklist**:
- [ ] Check DLQ stats
- [ ] Review failure patterns
- [ ] Archive old resolved failures
- [ ] Update runbooks with new patterns
- [ ] Test replay procedures

---

## Related Documentation

- [DLQ System Design](../DLQ_SYSTEM.md)
- [Celery Task Patterns](./CELERY_TASKS.md)
- [Idempotency Guide](./IDEMPOTENCY.md)
- [RabbitMQ Maintenance](./RABBITMQ_MAINTENANCE.md)

---

## Revision History

| Date       | Version | Author  | Changes |
|------------|---------|---------|---------|
| 2024-01-15 | 1.0     | DevOps  | Initial version |

---

## Emergency Contacts

- **On-Call Engineer**: oncall@example.com
- **Backend Team**: backend@example.com
- **Slack Channel**: #dlq-alerts
- **PagerDuty**: https://example.pagerduty.com/dlq
