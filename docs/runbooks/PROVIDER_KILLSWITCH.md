# Provider Kill-Switch Runbook

## Overview

This runbook provides procedures for quickly disabling problematic third-party service providers (email, SMS, data enrichment) when issues are detected, and safely re-enabling them once resolved.

**Audience**: DevOps Engineers, On-Call Engineers, SRE Team
**Prerequisites**: API access, database access, environment variable access
**Estimated Time**: 5-15 minutes (emergency) / 30-60 minutes (planned)
**Risk Level**: High - affects customer-facing functionality

---

## Table of Contents

1. [When to Use Kill-Switch](#when-to-use-kill-switch)
2. [Provider Overview](#provider-overview)
3. [Emergency Kill-Switch](#emergency-kill-switch)
4. [Planned Disable](#planned-disable)
5. [Provider-Specific Procedures](#provider-specific-procedures)
6. [Monitoring and Alerts](#monitoring-and-alerts)
7. [Re-enabling Providers](#re-enabling-providers)
8. [Fallback Strategies](#fallback-strategies)

---

## When to Use Kill-Switch

### Emergency Scenarios (Immediate Kill-Switch)

1. **Provider Outage**: Service completely unavailable
2. **API Rate Limit Abuse**: Unexpected high rate limit usage/costs
3. **Data Corruption**: Provider returning corrupt/invalid data
4. **Security Incident**: Compromised API keys or suspicious activity
5. **Billing Issues**: Unexpected charges or account suspension
6. **Compliance Violation**: Provider action causing regulatory issues

### Planned Scenarios (Scheduled Disable)

1. **Provider Migration**: Switching to alternative provider
2. **Cost Optimization**: Temporarily reducing usage
3. **Testing/Validation**: Testing without production traffic
4. **Maintenance Window**: Provider scheduled maintenance

### When NOT to Use

- Temporary network glitches (let retry logic handle)
- Single failed request (investigate first)
- Slow responses (adjust timeouts first)
- Minor errors (< 1% failure rate)

---

## Provider Overview

### Integrated Providers

| Provider | Purpose | Kill-Switch Method | Impact Level |
|----------|---------|-------------------|--------------|
| SendGrid | Email delivery | ENV var + queue pause | High |
| Twilio | SMS delivery | ENV var + queue pause | High |
| Mailgun | Email backup | ENV var | Medium |
| Plivo | SMS backup | ENV var | Medium |
| Melissa | Address validation | Feature flag | Low |
| Whitepages | Owner lookup | Feature flag | Low |
| OpenCage | Geocoding | Feature flag | Low |

### Provider Dependencies

```
Email Communications → SendGrid (primary) → Mailgun (failover)
SMS Communications → Twilio (primary) → Plivo (failover)
Property Enrichment → Melissa + Whitepages + OpenCage (parallel)
```

---

## Emergency Kill-Switch

### Immediate Action (< 5 minutes)

#### Step 1: Identify Provider

```bash
# Check which provider is failing
# Review recent errors
docker logs api-1 | grep -i "error" | tail -50

# Check specific provider logs
docker logs api-1 | grep -i "sendgrid\|twilio\|mailgun"

# Identify from alerts
# Check Slack #ops-alerts or PagerDuty
```

#### Step 2: Disable Provider

**Option A: Environment Variable (Fastest)**

```bash
# For Kubernetes
kubectl set env deployment/api SENDGRID_ENABLED=false
kubectl set env deployment/celery-worker SENDGRID_ENABLED=false

# For Docker Compose
docker-compose stop
# Edit .env file
echo "SENDGRID_ENABLED=false" >> .env
docker-compose up -d

# For system env
export SENDGRID_ENABLED=false
sudo systemctl restart api celery-worker
```

**Option B: Feature Flag (Database)**

```sql
-- Connect to database
psql -U postgres -d realestateos

-- Disable provider
INSERT INTO feature_flags (name, enabled, updated_at)
VALUES ('provider_sendgrid', false, NOW())
ON CONFLICT (name) DO UPDATE
SET enabled = false, updated_at = NOW();

-- Verify
SELECT * FROM feature_flags WHERE name LIKE 'provider_%';
```

**Option C: Configuration File**

```bash
# Edit provider config
vim /etc/realestateos/providers.yaml

# Set enabled: false for provider
providers:
  email:
    sendgrid:
      enabled: false  # Changed from true
      api_key: $SENDGRID_API_KEY

# Reload configuration
kill -HUP $(cat /var/run/api.pid)
```

#### Step 3: Pause Affected Queues

```bash
# Pause email queue
celery -A api.celery_app control  cancel_consumer emails
celery -A api.celery_app control cancel_consumer memos

# Pause SMS queue
celery -A api.celery_app control cancel_consumer sms

# Verify queues paused
celery -A api.celery_app inspect active_queues
```

#### Step 4: Notify Team

```bash
# Slack notification
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"🚨 KILL-SWITCH ACTIVATED: SendGrid disabled due to outage"}' \
  $SLACK_WEBHOOK_URL

# PagerDuty incident
curl -X POST https://api.pagerduty.com/incidents \
  -H "Authorization: Token token=$PAGERDUTY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "incident": {
      "type": "incident",
      "title": "Provider Kill-Switch: SendGrid",
      "service": {"id": "SERVICE_ID", "type": "service_reference"},
      "urgency": "high",
      "body": {
        "type": "incident_body",
        "details": "SendGrid disabled via kill-switch"
      }
    }
  }'
```

### Verification

```bash
# Verify provider disabled
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  https://api.realestateos.com/api/v1/admin/providers/status

# Expected response:
# {
#   "sendgrid": {"enabled": false, "reason": "kill_switch"},
#   "twilio": {"enabled": true},
#   ...
# }

# Check no new requests to disabled provider
docker logs api-1 | grep -i "sendgrid" | tail -20
# Should show no new API calls

# Verify failover working (if configured)
# Check logs for fallback provider usage
docker logs api-1 | grep -i "mailgun" | tail -20
```

---

## Planned Disable

### Pre-Disable Checklist

- [ ] Notify team in #engineering (24h advance notice)
- [ ] Check current queue depths
- [ ] Verify fallback provider configured
- [ ] Review scheduled communications
- [ ] Create runbook ticket/issue
- [ ] Schedule disable during low-traffic window

### Step-by-Step Process

#### 1. Drain Current Queue

```bash
# Check queue depth
celery -A api.celery_app inspect reserved | grep emails

# Wait for queue to drain or set deadline
# Monitor: should reach 0 or acceptable level
watch -n 5 'celery -A api.celery_app inspect reserved | grep -A 5 emails'
```

#### 2. Enable Failover (If Available)

```bash
# Activate backup provider first
kubectl set env deployment/api MAILGUN_ENABLED=true

# Verify failover ready
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  https://api.realestateos.com/api/v1/admin/providers/health/mailgun
```

#### 3. Disable Primary Provider

```bash
# Use feature flag for graceful disable
psql -U postgres -d realestateos -c "
  UPDATE feature_flags
  SET enabled = false
  WHERE name = 'provider_sendgrid';"

# Or environment variable
kubectl set env deployment/api SENDGRID_ENABLED=false
```

#### 4. Monitor Transition

```bash
# Watch for errors
kubectl logs -f deployment/api | grep -i "email\|error"

# Check failover usage
kubectl logs -f deployment/api | grep -i "mailgun"

# Monitor success rate
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  https://api.realestateos.com/api/v1/admin/stats/email-delivery
```

---

## Provider-Specific Procedures

### SendGrid (Email)

**Kill-Switch:**
```bash
# 1. Disable via ENV
kubectl set env deployment/api SENDGRID_ENABLED=false
kubectl set env deployment/celery-worker SENDGRID_ENABLED=false

# 2. Revoke API key (if compromised)
curl -X DELETE https://api.sendgrid.com/v3/api_keys/$KEY_ID \
  -H "Authorization: Bearer $SENDGRID_MASTER_KEY"

# 3. Pause email queues
celery -A api.celery_app control cancel_consumer emails
celery -A api.celery_app control cancel_consumer memos
```

**Failover:** Automatically routes to Mailgun if `MAILGUN_ENABLED=true`

**Impact:** High - all outbound emails blocked

### Twilio (SMS)

**Kill-Switch:**
```bash
# 1. Disable via ENV
kubectl set env deployment/api TWILIO_ENABLED=false

# 2. Suspend Twilio account (if compromised)
curl -X POST https://api.twilio.com/2010-04-01/Accounts/$ACCOUNT_SID.json \
  -u "$ACCOUNT_SID:$AUTH_TOKEN" \
  -d "Status=suspended"

# 3. Pause SMS queue
celery -A api.celery_app control cancel_consumer sms
```

**Failover:** Routes to Plivo if configured

**Impact:** High - all SMS messages blocked

### Data Enrichment Providers

**Kill-Switch:**
```bash
# Disable specific enrichment providers
kubectl set env deployment/api MELISSA_ENABLED=false
kubectl set env deployment/api WHITEPAGES_ENABLED=false
kubectl set env deployment/api OPENCAGE_ENABLED=false

# Or pause enrichment queue
celery -A api.celery_app control cancel_consumer enrichment
```

**Failover:** N/A - enrichment is non-critical

**Impact:** Low - properties won't be enriched, but core functionality works

---

## Monitoring and Alerts

### Key Metrics

```sql
-- Provider health metrics
SELECT
  provider_name,
  COUNT(*) FILTER (WHERE status = 'success') as successes,
  COUNT(*) FILTER (WHERE status = 'failure') as failures,
  ROUND(
    COUNT(*) FILTER (WHERE status = 'failure')::numeric / COUNT(*) * 100,
    2
  ) as failure_rate
FROM provider_requests
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY provider_name;

-- Recent errors
SELECT
  provider_name,
  error_type,
  COUNT(*) as count
FROM provider_errors
WHERE created_at > NOW() - INTERVAL '15 minutes'
GROUP BY provider_name, error_type
ORDER BY count DESC;
```

### Dashboard

```bash
# Grafana dashboard for providers
# URL: https://grafana.realestateos.com/d/providers

# Key panels:
# - Provider availability (%)
# - Request rate per provider
# - Error rate per provider
# - Response time P95
# - Cost per provider (if available)
```

---

## Re-enabling Providers

### Prerequisites

- [ ] Root cause identified and resolved
- [ ] Provider confirms service restored
- [ ] Test requests successful
- [ ] Team notified of re-enable plan
- [ ] Monitoring dashboard reviewed

### Gradual Re-enable

#### 1. Test Provider Health

```bash
# Test API connectivity
curl -X POST https://api.sendgrid.com/v3/mail/send \
  -H "Authorization: Bearer $SENDGRID_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "personalizations": [{"to": [{"email": "test@example.com"}]}],
    "from": {"email": "noreply@realestateos.com"},
    "subject": "Test",
    "content": [{"type": "text/plain", "value": "Test"}]
  }'

# Should return 202 Accepted
```

#### 2. Enable with Canary

```bash
# Enable for 10% of traffic
kubectl set env deployment/api SENDGRID_ENABLED=true
kubectl set env deployment/api SENDGRID_ROLLOUT_PERCENTAGE=10

# Monitor for 15 minutes
watch -n 30 'kubectl logs deployment/api | grep sendgrid | grep error | wc -l'
```

#### 3. Gradual Rollout

```bash
# Increase to 50%
kubectl set env deployment/api SENDGRID_ROLLOUT_PERCENTAGE=50

# Monitor for 15 minutes

# Full rollout
kubectl set env deployment/api SENDGRID_ROLLOUT_PERCENTAGE=100

# Resume queues
celery -A api.celery_app control add_consumer emails
celery -A api.celery_app control add_consumer memos
```

#### 4. Disable Failover (If Applicable)

```bash
# Once primary stable, disable backup
kubectl set env deployment/api MAILGUN_ENABLED=false

# Keep as failover option
# Or set to fallback-only mode
kubectl set env deployment/api MAILGUN_FALLBACK_ONLY=true
```

---

## Fallback Strategies

### Email Fallback Chain

```
SendGrid (primary) →
  Failure Detection →
    Mailgun (secondary) →
      Failure Detection →
        DLQ for manual processing
```

### SMS Fallback Chain

```
Twilio (primary) →
  Failure Detection →
    Plivo (secondary) →
      Failure Detection →
        DLQ for manual processing
```

### Manual Intervention

When all providers fail:

```bash
# 1. Export queued messages
celery -A api.celery_app inspect reserved > /tmp/queued_messages.json

# 2. Archive to DLQ
python scripts/queue_to_dlq.py /tmp/queued_messages.json

# 3. Set up manual processing
# - Export contact list
# - Use alternative email client (Gmail, Outlook)
# - Track manually in spreadsheet
# - Update database when sent
```

---

## Post-Incident Review

After using kill-switch, conduct review:

1. **Timeline**: When did issue start/end?
2. **Root Cause**: What caused the problem?
3. **Impact**: How many users/operations affected?
4. **Response Time**: How quickly was kill-switch activated?
5. **Effectiveness**: Did kill-switch prevent further damage?
6. **Improvements**: What can be improved?

**Template:**

```markdown
## Incident: Provider Kill-Switch Activation

**Date**: 2024-01-15
**Provider**: SendGrid
**Duration**: 45 minutes
**Triggered By**: DevOps Engineer (John Doe)

### Timeline
- 14:00 - Provider outage detected
- 14:05 - Kill-switch activated
- 14:10 - Failover to Mailgun confirmed
- 14:45 - Provider restored, gradual re-enable started
- 15:30 - Full service restored

### Impact
- 234 emails queued (successfully sent via Mailgun)
- 0 emails lost
- No customer-facing impact

### Root Cause
SendGrid API gateway failure (their side)

### Action Items
- [ ] Add automated kill-switch trigger for >50% error rate
- [ ] Improve failover detection speed
- [ ] Document lessons learned
```

---

## Related Documentation

- [Provider Integration Guide](./PROVIDER_INTEGRATION.md)
- [Failover Configuration](./FAILOVER_CONFIG.md)
- [DLQ Replay Runbook](./DLQ_REPLAY.md)
- [Incident Response Plan](./INCIDENT_RESPONSE.md)

---

## Revision History

| Date       | Version | Author  | Changes |
|------------|---------|---------|---------|
| 2024-01-15 | 1.0     | DevOps  | Initial version |

---

## Emergency Contacts

- **On-Call Engineer**: oncall@example.com
- **Provider Support**: See provider-specific contacts below
  - SendGrid: support@sendgrid.com
  - Twilio: support@twilio.com
- **Slack Channel**: #ops-critical
- **PagerDuty**: https://example.pagerduty.com/providers
