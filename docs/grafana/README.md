# Grafana Dashboards for Real Estate OS

This directory contains pre-configured Grafana dashboard JSON files for monitoring Real Estate OS platform metrics.

## Available Dashboards

### 1. DLQ Monitoring (`dlq-dashboard.json`)
Monitors the Dead Letter Queue (DLQ) for failed Celery tasks.

**Key Metrics:**
- DLQ depth (total failed tasks)
- Failed tasks by queue and task type
- Oldest failure age
- Replay success rate
- Replay duration (P95)
- Celery queue depth
- Task execution status

**Alerts:**
- DLQ depth > 0 for > 5 minutes

**Use Cases:**
- Identify which tasks are failing
- Monitor DLQ replay operations
- Track task execution health

### 2. Portfolio Reconciliation (`reconciliation-dashboard.json`)
Tracks portfolio reconciliation validation with ±0.5% threshold compliance.

**Key Metrics:**
- Reconciliation pass rate
- Total validations performed
- Properties checked
- Discrepancy percentage by portfolio
- Reconciliation duration (P50, P95, P99)
- Threshold compliance (±0.5%)

**Alerts:**
- Reconciliation failure for > 10 minutes (discrepancy > ±0.5%)

**Use Cases:**
- Monitor portfolio data integrity
- Identify portfolios with discrepancies
- Track reconciliation performance

### 3. Rate Limiting (`rate-limiting-dashboard.json`)
Monitors API rate limiting and potential abuse.

**Key Metrics:**
- Total rate limit hits
- Hit rate (requests/sec)
- Affected users count
- Average remaining quota
- Top rate-limited users
- Top rate-limited endpoints
- Success vs rate-limited request ratio

**Alerts:**
- High rate limit hits (> 100 in 5 minutes)

**Use Cases:**
- Detect API abuse
- Identify problematic clients
- Optimize rate limit thresholds
- Monitor API health

## Prerequisites

1. **Prometheus** - Collecting metrics from `/metrics` endpoint
2. **Grafana** - Version 9.0 or higher
3. **Real Estate OS API** - Running with Prometheus instrumentation enabled

## Installation

### Step 1: Set Up Prometheus

Add Real Estate OS API as a scrape target in `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'realestateos'
    scrape_interval: 15s
    static_configs:
      - targets: ['api:8000']  # Adjust host:port as needed
    metrics_path: '/metrics'
```

Restart Prometheus to apply changes:

```bash
docker-compose restart prometheus
# or
systemctl restart prometheus
```

### Step 2: Verify Metrics Collection

Check that Prometheus is collecting metrics:

```bash
# Visit Prometheus UI
http://localhost:9090

# Query a metric
realestateos_dlq_depth
```

### Step 3: Import Dashboards to Grafana

#### Option A: Via Grafana UI

1. Log in to Grafana (default: http://localhost:3000)
2. Navigate to **Dashboards** → **Import**
3. Click **Upload JSON file**
4. Select one of the dashboard JSON files
5. Choose your Prometheus data source
6. Click **Import**

Repeat for each dashboard.

#### Option B: Via Grafana API

```bash
# Set your Grafana credentials
GRAFANA_URL="http://localhost:3000"
GRAFANA_USER="admin"
GRAFANA_PASSWORD="admin"

# Import DLQ Dashboard
curl -X POST \
  -H "Content-Type: application/json" \
  -u "$GRAFANA_USER:$GRAFANA_PASSWORD" \
  -d @dlq-dashboard.json \
  "$GRAFANA_URL/api/dashboards/db"

# Import Reconciliation Dashboard
curl -X POST \
  -H "Content-Type: application/json" \
  -u "$GRAFANA_USER:$GRAFANA_PASSWORD" \
  -d @reconciliation-dashboard.json \
  "$GRAFANA_URL/api/dashboards/db"

# Import Rate Limiting Dashboard
curl -X POST \
  -H "Content-Type: application/json" \
  -u "$GRAFANA_USER:$GRAFANA_PASSWORD" \
  -d @rate-limiting-dashboard.json \
  "$GRAFANA_URL/api/dashboards/db"
```

#### Option C: Provisioning (Recommended for Production)

Create a Grafana provisioning file:

```yaml
# /etc/grafana/provisioning/dashboards/realestateos.yml
apiVersion: 1

providers:
  - name: 'RealEstateOS'
    orgId: 1
    folder: 'Real Estate OS'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards/realestateos
```

Copy dashboard files to the provisioning directory:

```bash
mkdir -p /var/lib/grafana/dashboards/realestateos
cp *.json /var/lib/grafana/dashboards/realestateos/
chown -R grafana:grafana /var/lib/grafana/dashboards
```

Restart Grafana:

```bash
systemctl restart grafana-server
```

## Configuration

### Data Source

All dashboards expect a Prometheus data source named **"Prometheus"**. If your data source has a different name, you'll need to update it during import or edit the JSON files.

### Variables

Each dashboard includes template variables for filtering:

**DLQ Dashboard:**
- `$queue` - Filter by queue name

**Reconciliation Dashboard:**
- `$portfolio` - Filter by portfolio ID
- `$threshold` - Discrepancy threshold (default: 0.5%)

**Rate Limiting Dashboard:**
- `$endpoint` - Filter by API endpoint
- `$user` - Filter by user ID

### Alerts

Alerts are pre-configured but **disabled by default**. To enable:

1. Go to **Dashboard Settings** → **JSON Model**
2. Find the `alert` configuration for each panel
3. Add notification channels to the `notifications` array
4. Save the dashboard

Example:

```json
"alert": {
  "name": "DLQ Depth Alert",
  "notifications": [
    {"uid": "slack-alerts"},
    {"uid": "pagerduty"}
  ],
  ...
}
```

## Customization

### Adjusting Thresholds

You can customize color thresholds in the dashboard UI or by editing the JSON:

```json
"thresholds": {
  "mode": "absolute",
  "steps": [
    {"value": null, "color": "green"},
    {"value": 80, "color": "yellow"},    // Warning threshold
    {"value": 95, "color": "red"}         // Critical threshold
  ]
}
```

### Adding Panels

1. Click **Add Panel** in the dashboard
2. Select your visualization type
3. Configure the query:
   ```promql
   # Example: Custom metric
   rate(realestateos_memo_generation_total[5m])
   ```
4. Save the panel

### Modifying Refresh Rate

Change auto-refresh interval in dashboard settings:
- Top right → Refresh dropdown
- Or edit JSON: `"refresh": "30s"`

## Troubleshooting

### No Data Showing

1. **Check Prometheus is scraping metrics:**
   ```bash
   curl http://localhost:8000/metrics
   ```
   Should return Prometheus metrics in text format.

2. **Verify Prometheus target is UP:**
   - Visit http://localhost:9090/targets
   - Check that `realestateos` target is UP

3. **Query Prometheus directly:**
   ```promql
   up{job="realestateos"}
   ```
   Should return `1` if the target is reachable.

4. **Check Grafana data source:**
   - Configuration → Data Sources → Prometheus
   - Click "Test" to verify connection

### Metrics Not Updating

1. **Check API is running:**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Verify metrics collection is enabled:**
   ```bash
   # Check for ENABLE_METRICS env var
   echo $ENABLE_METRICS  # Should be "true" or "1"
   ```

3. **Review API logs:**
   ```bash
   docker logs api-1 | grep metrics
   ```

### Dashboard Import Fails

1. **Check Grafana version compatibility:**
   - These dashboards require Grafana 9.0+
   - Update Grafana if needed

2. **Validate JSON syntax:**
   ```bash
   python -m json.tool dlq-dashboard.json > /dev/null
   ```

3. **Check for data source mismatch:**
   - Ensure Prometheus data source exists before importing

## Best Practices

1. **Set Up Alerts**
   - Configure Slack/PagerDuty/Email notifications
   - Test alerts after configuration

2. **Create Dashboard Snapshots**
   - For incident reviews and post-mortems
   - Share → Snapshot → Publish to Grafana Cloud

3. **Use Variables**
   - Filter by team, environment, or time range
   - Reduce dashboard clutter

4. **Regular Review**
   - Weekly: Check DLQ depth, reconciliation pass rate
   - Daily: Monitor rate limiting for abuse
   - Monthly: Review dashboard effectiveness

5. **Version Control**
   - Export dashboards after changes
   - Commit JSON files to Git
   - Use Grafana provisioning for consistency

## Monitoring Checklist

- [ ] Prometheus collecting metrics from `/metrics`
- [ ] All three dashboards imported
- [ ] Data showing in dashboards (not "No data")
- [ ] Alerts configured with notification channels
- [ ] Dashboard variables working (dropdowns populated)
- [ ] Team trained on dashboard usage
- [ ] Dashboards added to ops runbooks

## Related Documentation

- [Prometheus Metrics](../api/metrics.py) - Metric definitions
- [DLQ Replay Runbook](../runbooks/DLQ_REPLAY.md)
- [PITR Recovery Runbook](../runbooks/PITR_RECOVERY.md)
- [Provider Kill-Switch Runbook](../runbooks/PROVIDER_KILLSWITCH.md)

## Support

For dashboard issues or customization requests:
- Slack: #ops-monitoring
- Email: devops@real-estate-os.com
- Grafana Docs: https://grafana.com/docs/

## Changelog

| Date       | Version | Changes                              |
|------------|---------|--------------------------------------|
| 2024-01-15 | 1.0     | Initial dashboard release            |
| 2024-01-15 | 1.0     | DLQ, Reconciliation, Rate Limiting   |
