# Operations Configuration

This directory contains operational configuration files for Real Estate OS infrastructure services.

## Directory Structure

```
ops/
├── prometheus/
│   └── prometheus.yml          # Prometheus scrape configuration
├── grafana/
│   └── provisioning/
│       ├── datasources/        # Auto-configured data sources
│       │   └── prometheus.yml
│       └── dashboards/         # Auto-loaded dashboards
│           └── default.yml
└── README.md
```

## Prometheus Configuration

**File**: `prometheus/prometheus.yml`

Scrapes metrics from all platform services:
- **API Service**: FastAPI metrics at `/metrics`
- **PostgreSQL**: Via postgres-exporter on port 9187
- **Redis**: Via redis-exporter on port 9121
- **Airflow**: Webserver metrics at `/admin/metrics`
- **Qdrant**: Vector database metrics
- **MinIO**: Object storage metrics
- **Neo4j**: Graph database metrics
- **Keycloak**: Authentication service metrics

### Metrics Endpoints

| Service | Target | Path | Interval |
|---------|--------|------|----------|
| API | api:8000 | /metrics | 10s |
| PostgreSQL | postgres-exporter:9187 | /metrics | 30s |
| Redis | redis-exporter:9121 | /metrics | 30s |
| Airflow | airflow-webserver:8081 | /admin/metrics | 30s |
| Qdrant | qdrant:6333 | /metrics | 30s |
| MinIO | minio:9000 | /minio/v2/metrics/cluster | 30s |
| Neo4j | neo4j:2004 | /metrics | 30s |
| Grafana | grafana:3000 | /metrics | 30s |
| Keycloak | keycloak:8080 | /metrics | 30s |

### Access Prometheus UI

Once deployed:
```bash
open http://localhost:9090
```

Query examples:
- `rate(http_requests_total[5m])` - Request rate
- `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))` - p95 latency
- `pg_stat_database_numbackends` - PostgreSQL connections

## Grafana Configuration

**Files**:
- `grafana/provisioning/datasources/prometheus.yml` - Auto-configures Prometheus and PostgreSQL datasources
- `grafana/provisioning/dashboards/default.yml` - Auto-loads dashboards from JSON directory

### Access Grafana UI

Once deployed:
```bash
open http://localhost:3000
```

Default credentials (change in `.env.staging`):
- Username: `admin`
- Password: See `GRAFANA_ADMIN_PASSWORD` in `.env.staging`

### Pre-configured Datasources

1. **Prometheus** (default)
   - URL: `http://prometheus:9090`
   - 15s scrape interval
   - Incremental querying enabled

2. **PostgreSQL**
   - Direct database access for operational queries
   - Connection details from environment variables

## Quick Start

1. **Start observability stack**:
   ```bash
   docker compose --env-file .env.staging -f docker-compose.staging.yml up -d prometheus grafana
   ```

2. **Verify Prometheus targets**:
   ```bash
   curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'
   ```

3. **Access Grafana**:
   ```bash
   open http://localhost:3000
   ```

4. **Import dashboards**:
   - Navigate to Dashboards → Import
   - Use dashboard IDs:
     - **1860**: Node Exporter Full
     - **3662**: PostgreSQL Database
     - **763**: Redis Dashboard
     - **11074**: FastAPI Dashboard

## Creating Custom Dashboards

1. Create dashboard JSON in `ops/grafana/provisioning/dashboards/json/`
2. Restart Grafana: `docker compose restart grafana`
3. Dashboard will auto-load on startup

## Troubleshooting

**Prometheus not scraping targets**:
```bash
# Check Prometheus logs
docker compose logs prometheus

# Verify network connectivity
docker compose exec prometheus wget -O- http://api:8000/metrics
```

**Grafana datasource errors**:
```bash
# Check Grafana logs
docker compose logs grafana

# Verify Prometheus is reachable
docker compose exec grafana wget -O- http://prometheus:9090/-/healthy
```

**Missing metrics**:
- Ensure service exporters are installed (postgres-exporter, redis-exporter)
- Check if service exposes metrics endpoint
- Verify firewall/network policies

## Alerting (Future)

To enable alerting:
1. Deploy Alertmanager: Add to `docker-compose.staging.yml`
2. Create alert rules in `ops/prometheus/alerts/*.yml`
3. Uncomment `alerting` and `rule_files` sections in `prometheus.yml`
4. Configure notification channels (Slack, PagerDuty, email)

## Related Scripts

- `scripts/ops/health_check.sh` - Verify all services are healthy
- `scripts/ops/apply_migrations.sh` - Apply database migrations
- `scripts/ops/verify_rls.sh` - Test cross-tenant isolation

## Resources

- [Prometheus Query Basics](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/)
- [PromQL Cheat Sheet](https://promlabs.com/promql-cheat-sheet/)
