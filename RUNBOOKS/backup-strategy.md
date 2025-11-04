# Backup & Restore Strategy

## Overview

Real Estate OS implements a comprehensive backup strategy for both PostgreSQL databases and MinIO object storage to ensure data durability and disaster recovery capabilities.

**Recovery Objectives:**
- **RPO (Recovery Point Objective)**: < 5 minutes
- **RTO (Recovery Time Objective)**: < 30 minutes

## PostgreSQL Backup Strategy

### Method: pgBackRest

We use **pgBackRest** for PostgreSQL backup and restore operations. pgBackRest provides:

- Full, differential, and incremental backups
- Point-in-Time Recovery (PITR)
- Parallel backup/restore
- Compression and encryption
- S3-compatible object storage support

### Backup Schedule

```
- Full Backup:       Weekly (Sunday 02:00 UTC)
- Differential:      Daily (02:00 UTC)
- Incremental:       Every 6 hours
- WAL Archiving:     Continuous
```

### Backup Retention

```
- Full backups:      4 weeks (28 days)
- Differential:      7 days
- Incremental:       7 days
- WAL archives:      7 days
```

### Configuration

#### pgBackRest Configuration (`/etc/pgbackrest/pgbackrest.conf`)

```ini
[global]
repo1-path=/var/lib/pgbackrest
repo1-retention-full=4
repo1-retention-diff=2
repo1-cipher-type=aes-256-cbc
repo1-cipher-pass=<encrypted-passphrase>

# S3 configuration for off-site backups
repo2-type=s3
repo2-s3-bucket=realestate-backups
repo2-s3-region=us-east-1
repo2-s3-endpoint=s3.amazonaws.com
repo2-s3-key=<aws-access-key>
repo2-s3-key-secret=<aws-secret-key>
repo2-retention-full=8
repo2-cipher-type=aes-256-cbc

# PostgreSQL settings
pg1-path=/var/lib/postgresql/14/main
pg1-port=5432
pg1-socket-path=/var/run/postgresql

# Archive settings
archive-async=y
archive-push-queue-max=1GB

# Backup settings
process-max=4
log-level-console=info
log-level-file=debug

[realestate-db]
pg1-path=/var/lib/postgresql/14/main
pg1-port=5432
```

#### PostgreSQL Configuration (`postgresql.conf`)

```ini
# WAL archiving
archive_mode = on
archive_command = 'pgbackrest --stanza=realestate-db archive-push %p'
archive_timeout = 300  # 5 minutes

# Replication
wal_level = replica
max_wal_senders = 3
max_replication_slots = 3

# PITR settings
hot_standby = on
wal_log_hints = on
```

### Backup Commands

#### Create Stanza (Initial Setup)

```bash
sudo -u postgres pgbackrest --stanza=realestate-db stanza-create
```

#### Full Backup

```bash
sudo -u postgres pgbackrest --stanza=realestate-db --type=full backup
```

#### Differential Backup

```bash
sudo -u postgres pgbackrest --stanza=realestate-db --type=diff backup
```

#### Incremental Backup

```bash
sudo -u postgres pgbackrest --stanza=realestate-db --type=incr backup
```

#### Check Backup Status

```bash
sudo -u postgres pgbackrest --stanza=realestate-db info
```

### Automated Backup (Cron)

```cron
# Full backup every Sunday at 02:00 UTC
0 2 * * 0 postgres pgbackrest --stanza=realestate-db --type=full backup

# Differential backup every day (except Sunday) at 02:00 UTC
0 2 * * 1-6 postgres pgbackrest --stanza=realestate-db --type=diff backup

# Incremental backup every 6 hours
0 */6 * * * postgres pgbackrest --stanza=realestate-db --type=incr backup
```

## MinIO Object Storage Backup Strategy

### Method: Versioning + Lifecycle Policies

MinIO provides built-in versioning and lifecycle management for object storage.

### Versioning Configuration

```bash
# Enable versioning on buckets
mc version enable myminio/realestate-memos
mc version enable myminio/realestate-documents
mc version enable myminio/realestate-exports
```

### Lifecycle Policies

#### Memo Bucket Policy (`memo-lifecycle.json`)

```json
{
  "Rules": [
    {
      "ID": "DeleteOldVersions",
      "Status": "Enabled",
      "Expiration": {
        "Days": 90
      },
      "NoncurrentVersionExpiration": {
        "NoncurrentDays": 30
      }
    }
  ]
}
```

#### Apply Lifecycle Policy

```bash
mc ilm import myminio/realestate-memos < memo-lifecycle.json
```

### Replication Configuration

MinIO supports bucket replication to a secondary site for disaster recovery.

```bash
# Add remote site
mc admin bucket remote add myminio/realestate-memos \
  https://backup-minio.example.com/realestate-memos \
  --service "replication" \
  --access-key <access-key> \
  --secret-key <secret-key>

# Enable replication
mc replicate add myminio/realestate-memos \
  --remote-bucket arn:minio:replication::<remote-id>:realestate-memos \
  --priority 1
```

### MinIO Backup Commands

#### Export Bucket Metadata

```bash
mc admin config export myminio > minio-config-backup.json
```

#### Mirror Bucket to Secondary Site

```bash
mc mirror --watch myminio/realestate-memos s3backup/realestate-memos
```

## Monitoring & Alerting

### Backup Monitoring

```prometheus
# Prometheus metrics
pgbackrest_last_full_backup_age_seconds
pgbackrest_last_diff_backup_age_seconds
pgbackrest_backup_success_total
pgbackrest_backup_failure_total

minio_bucket_versioning_enabled
minio_bucket_replication_lag_seconds
```

### Alerts

```yaml
# Alert if full backup is older than 8 days
- alert: PostgresFullBackupOld
  expr: pgbackrest_last_full_backup_age_seconds > 691200  # 8 days
  for: 1h
  annotations:
    summary: PostgreSQL full backup is older than 8 days
    description: Last full backup was {{ $value | humanizeDuration }} ago

# Alert if WAL archiving fails
- alert: PostgresWALArchivingFailed
  expr: rate(pgbackrest_archive_push_failure_total[5m]) > 0
  for: 5m
  annotations:
    summary: PostgreSQL WAL archiving is failing
    description: WAL archive push failures detected

# Alert if MinIO versioning is disabled
- alert: MinIOVersioningDisabled
  expr: minio_bucket_versioning_enabled == 0
  for: 1m
  annotations:
    summary: MinIO bucket versioning is disabled
    description: Versioning is disabled on {{ $labels.bucket }}
```

## Backup Verification

### Weekly Backup Tests

Every week, we perform automated backup verification:

1. **Restore to staging**: Restore latest backup to staging database
2. **Data validation**: Run SQL queries to validate row counts
3. **Performance test**: Run read queries to ensure indexes are intact
4. **Report**: Generate backup verification report

```bash
#!/bin/bash
# Automated backup verification script
# Run weekly: Sunday 04:00 UTC

STAGING_DB="realestate_staging"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
REPORT_FILE="/var/log/backup-verification-$TIMESTAMP.log"

echo "Backup Verification: $TIMESTAMP" | tee $REPORT_FILE

# 1. Stop staging database
sudo systemctl stop postgresql-staging

# 2. Restore latest backup
sudo -u postgres pgbackrest --stanza=realestate-db \
  --delta --type=time --target="latest" \
  --pg1-path=/var/lib/postgresql/staging \
  restore | tee -a $REPORT_FILE

# 3. Start staging database
sudo systemctl start postgresql-staging

# 4. Run validation queries
psql -h localhost -U realestate_app -d $STAGING_DB <<EOF | tee -a $REPORT_FILE
-- Row counts
SELECT 'properties' as table, COUNT(*) FROM properties;
SELECT 'pipeline_state' as table, COUNT(*) FROM pipeline_state;
SELECT 'timeline_entries' as table, COUNT(*) FROM timeline_entries;
SELECT 'action_packets' as table, COUNT(*) FROM action_packets;

-- Recent activity
SELECT MAX(created_at) as last_property FROM properties;
SELECT MAX(state_changed_at) as last_state_change FROM pipeline_state;
EOF

echo "Verification complete: $TIMESTAMP" | tee -a $REPORT_FILE

# 5. Upload report to S3
aws s3 cp $REPORT_FILE s3://realestate-ops/backup-verification/
```

## Disaster Recovery Procedures

See [RUNBOOKS/restore.md](./restore.md) for detailed disaster recovery procedures including:

- Point-in-Time Recovery (PITR)
- Full database restore
- Object storage restore
- Failover procedures

## Compliance & Security

### Encryption

- **At Rest**: AES-256-CBC encryption for all backups
- **In Transit**: TLS 1.2+ for all backup transfers
- **Key Management**: AWS KMS for encryption keys

### Access Control

- Backup files: Read-only for postgres user, ops team
- Restore operations: Requires ops role + MFA
- S3 buckets: IAM policies with least privilege

### Audit Logging

All backup and restore operations are logged to:
- PostgreSQL audit log
- pgBackRest log files
- CloudWatch Logs (AWS)
- Splunk (centralized logging)

### Retention Policy

- **Production backups**: 30 days (local) + 90 days (S3)
- **Audit logs**: 7 years (compliance requirement)
- **Deleted data**: 90 days (soft delete + versioning)

## Cost Optimization

### Backup Storage Costs

```
Local (pgBackRest):
- Full backup:       ~50 GB (compressed)
- Daily differential: ~5 GB
- Total local:       ~200 GB

S3 (off-site):
- Full backups (8 weeks): ~400 GB
- S3 Standard:       $9.20/month
- S3 Glacier (90d+): $1.64/month

Total backup costs: ~$11/month
```

### Optimization Strategies

1. **Compression**: Enable pgBackRest compression (60-70% reduction)
2. **Deduplication**: Incremental backups only store changes
3. **Lifecycle policies**: Move old backups to S3 Glacier
4. **Multi-region**: Replicate critical backups to secondary region

## References

- [pgBackRest Documentation](https://pgbackrest.org/user-guide.html)
- [PostgreSQL PITR](https://www.postgresql.org/docs/14/continuous-archiving.html)
- [MinIO Versioning](https://docs.min.io/docs/minio-bucket-versioning-guide.html)
- [AWS S3 Lifecycle](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)

**Last Updated**: 2025-11-03
**Owner**: DevOps Team
**Review Cycle**: Quarterly
