"""
Prometheus Metrics for Real Estate OS

Exposes custom metrics for monitoring:
- DLQ (Dead Letter Queue) depth and processing
- Portfolio reconciliation validation
- Rate limiting
- API performance
- Background job processing
"""
from prometheus_client import Counter, Gauge, Histogram, Summary, Info
from typing import Optional
import time

# ============================================================================
# API METRICS
# ============================================================================

# Request metrics (automatically handled by instrumentator, but can add custom)
api_requests_total = Counter(
    'realestateos_api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

api_request_duration_seconds = Histogram(
    'realestateos_api_request_duration_seconds',
    'API request duration in seconds',
    ['method', 'endpoint'],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0)
)

# ============================================================================
# DLQ (DEAD LETTER QUEUE) METRICS
# ============================================================================

dlq_depth = Gauge(
    'realestateos_dlq_depth',
    'Number of failed tasks in Dead Letter Queue',
    ['queue_name', 'task_name']
)

dlq_replay_total = Counter(
    'realestateos_dlq_replay_total',
    'Total number of DLQ tasks replayed',
    ['queue_name', 'status']
)

dlq_replay_duration_seconds = Histogram(
    'realestateos_dlq_replay_duration_seconds',
    'Duration of DLQ replay operations',
    ['queue_name'],
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0)
)

dlq_oldest_failure_age_seconds = Gauge(
    'realestateos_dlq_oldest_failure_age_seconds',
    'Age of oldest failure in DLQ (seconds)',
    ['queue_name']
)

# ============================================================================
# PORTFOLIO RECONCILIATION METRICS
# ============================================================================

reconciliation_validation_total = Counter(
    'realestateos_reconciliation_validation_total',
    'Total reconciliation validations performed',
    ['status']
)

reconciliation_discrepancy_percentage = Gauge(
    'realestateos_reconciliation_discrepancy_percentage',
    'Portfolio reconciliation discrepancy percentage',
    ['portfolio_id']
)

reconciliation_duration_seconds = Histogram(
    'realestateos_reconciliation_duration_seconds',
    'Duration of portfolio reconciliation',
    buckets=(0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0)
)

reconciliation_properties_checked = Counter(
    'realestateos_reconciliation_properties_checked_total',
    'Total properties checked during reconciliation'
)

reconciliation_failures = Counter(
    'realestateos_reconciliation_failures_total',
    'Total reconciliation failures (outside ±0.5% threshold)',
    ['portfolio_id']
)

# ============================================================================
# RATE LIMITING METRICS
# ============================================================================

rate_limit_hits_total = Counter(
    'realestateos_rate_limit_hits_total',
    'Total requests that hit rate limits',
    ['endpoint', 'user_id']
)

rate_limit_remaining = Gauge(
    'realestateos_rate_limit_remaining',
    'Remaining requests in rate limit window',
    ['endpoint', 'user_id']
)

rate_limit_reset_seconds = Gauge(
    'realestateos_rate_limit_reset_seconds',
    'Seconds until rate limit window resets',
    ['endpoint', 'user_id']
)

# ============================================================================
# COMMUNICATION METRICS
# ============================================================================

memo_generation_total = Counter(
    'realestateos_memo_generation_total',
    'Total memos generated',
    ['template_id', 'status']
)

memo_generation_duration_seconds = Histogram(
    'realestateos_memo_generation_duration_seconds',
    'Memo generation duration',
    ['template_id'],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
)

email_delivery_total = Counter(
    'realestateos_email_delivery_total',
    'Total emails sent',
    ['provider', 'status']
)

sms_delivery_total = Counter(
    'realestateos_sms_delivery_total',
    'Total SMS messages sent',
    ['provider', 'status']
)

# ============================================================================
# WEBHOOK METRICS
# ============================================================================

webhook_received_total = Counter(
    'realestateos_webhook_received_total',
    'Total webhooks received',
    ['provider', 'event_type']
)

webhook_signature_validation_total = Counter(
    'realestateos_webhook_signature_validation_total',
    'Webhook signature validations',
    ['provider', 'status']
)

webhook_processing_duration_seconds = Histogram(
    'realestateos_webhook_processing_duration_seconds',
    'Webhook processing duration',
    ['provider', 'event_type'],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 5.0)
)

# ============================================================================
# IDEMPOTENCY METRICS
# ============================================================================

idempotency_cache_hits = Counter(
    'realestateos_idempotency_cache_hits_total',
    'Total idempotency cache hits (duplicate requests)'
)

idempotency_cache_misses = Counter(
    'realestateos_idempotency_cache_misses_total',
    'Total idempotency cache misses (new requests)'
)

# ============================================================================
# BACKGROUND JOB METRICS
# ============================================================================

celery_task_total = Counter(
    'realestateos_celery_task_total',
    'Total Celery tasks executed',
    ['task_name', 'status']
)

celery_task_duration_seconds = Histogram(
    'realestateos_celery_task_duration_seconds',
    'Celery task execution duration',
    ['task_name'],
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0)
)

celery_queue_depth = Gauge(
    'realestateos_celery_queue_depth',
    'Number of tasks in Celery queue',
    ['queue_name']
)

# ============================================================================
# SSE (SERVER-SENT EVENTS) METRICS
# ============================================================================

sse_connections_active = Gauge(
    'realestateos_sse_connections_active',
    'Number of active SSE connections',
    ['team_id']
)

sse_events_sent_total = Counter(
    'realestateos_sse_events_sent_total',
    'Total SSE events sent',
    ['event_type', 'team_id']
)

sse_connection_duration_seconds = Summary(
    'realestateos_sse_connection_duration_seconds',
    'SSE connection duration'
)

# ============================================================================
# DATABASE METRICS
# ============================================================================

database_query_duration_seconds = Histogram(
    'realestateos_database_query_duration_seconds',
    'Database query duration',
    ['operation'],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0)
)

database_connections_active = Gauge(
    'realestateos_database_connections_active',
    'Number of active database connections'
)

# ============================================================================
# BUSINESS METRICS
# ============================================================================

properties_total = Gauge(
    'realestateos_properties_total',
    'Total properties in system',
    ['stage']
)

users_total = Gauge(
    'realestateos_users_total',
    'Total users in system'
)

teams_total = Gauge(
    'realestateos_teams_total',
    'Total teams in system'
)

# ============================================================================
# PROVIDER METRICS
# ============================================================================

provider_requests_total = Counter(
    'realestateos_provider_requests_total',
    'Total requests to external providers',
    ['provider', 'operation', 'status']
)

provider_request_duration_seconds = Histogram(
    'realestateos_provider_request_duration_seconds',
    'External provider request duration',
    ['provider', 'operation'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
)

provider_enabled = Gauge(
    'realestateos_provider_enabled',
    'Whether provider is enabled (1=enabled, 0=disabled)',
    ['provider']
)

# ============================================================================
# APPLICATION INFO
# ============================================================================

app_info = Info('realestateos_app', 'Real Estate OS application information')
app_info.info({
    'version': '1.0.0',
    'name': 'Real Estate OS',
    'environment': 'production'
})

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

class MetricsTimer:
    """Context manager for timing operations"""
    def __init__(self, histogram, *labels):
        self.histogram = histogram
        self.labels = labels
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        if self.labels:
            self.histogram.labels(*self.labels).observe(duration)
        else:
            self.histogram.observe(duration)

def update_dlq_metrics(db_session):
    """Update DLQ metrics from database"""
    from sqlalchemy import func, text
    from datetime import datetime

    try:
        # Get DLQ depth by queue and task
        result = db_session.execute(text("""
            SELECT queue_name, task_name, COUNT(*) as count
            FROM failed_tasks
            WHERE status = 'failed'
            GROUP BY queue_name, task_name
        """))

        for row in result:
            dlq_depth.labels(
                queue_name=row.queue_name or 'unknown',
                task_name=row.task_name or 'unknown'
            ).set(row.count)

        # Get oldest failure age
        result = db_session.execute(text("""
            SELECT queue_name, MIN(failed_at) as oldest
            FROM failed_tasks
            WHERE status = 'failed'
            GROUP BY queue_name
        """))

        now = datetime.utcnow()
        for row in result:
            if row.oldest:
                age_seconds = (now - row.oldest).total_seconds()
                dlq_oldest_failure_age_seconds.labels(
                    queue_name=row.queue_name or 'unknown'
                ).set(age_seconds)

    except Exception as e:
        print(f"Error updating DLQ metrics: {e}")

def update_business_metrics(db_session):
    """Update business metrics from database"""
    from sqlalchemy import func, text

    try:
        # Properties by stage
        result = db_session.execute(text("""
            SELECT current_stage, COUNT(*) as count
            FROM properties
            WHERE deleted_at IS NULL
            GROUP BY current_stage
        """))

        for row in result:
            properties_total.labels(
                stage=row.current_stage or 'unknown'
            ).set(row.count)

        # Total users
        result = db_session.execute(text("""
            SELECT COUNT(*) as count
            FROM users
            WHERE deleted_at IS NULL
        """))

        count = result.scalar()
        if count:
            users_total.set(count)

        # Total teams
        result = db_session.execute(text("""
            SELECT COUNT(*) as count
            FROM teams
            WHERE deleted_at IS NULL
        """))

        count = result.scalar()
        if count:
            teams_total.set(count)

    except Exception as e:
        print(f"Error updating business metrics: {e}")

def update_all_metrics(db_session):
    """Update all database-derived metrics"""
    update_dlq_metrics(db_session)
    update_business_metrics(db_session)
