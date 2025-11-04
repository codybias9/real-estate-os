# Point-in-Time Recovery (PITR) Runbook

## Overview

This runbook provides step-by-step instructions for performing Point-in-Time Recovery (PITR) of the Real Estate OS database using PostgreSQL's continuous archiving and WAL (Write-Ahead Logging) features.

**Audience**: DevOps Engineers, Database Administrators
**Prerequisites**: PostgreSQL admin access, backup storage access
**Estimated Time**: 30-60 minutes
**Risk Level**: High - requires database downtime

---

## Table of Contents

1. [When to Use PITR](#when-to-use-pitr)
2. [Prerequisites](#prerequisites)
3. [Recovery Process](#recovery-process)
4. [Verification](#verification)
5. [Troubleshooting](#troubleshooting)
6. [Rollback](#rollback)

---

## When to Use PITR

Use PITR in the following scenarios:

- **Data Corruption**: Accidental deletion or modification of critical data
- **Application Bug**: Bug that corrupted data at a specific time
- **Security Incident**: Unauthorized data modification
- **Failed Migration**: Database migration that needs to be reverted

**DO NOT use PITR for**:
- Regular backups (use scheduled backups instead)
- Hardware failures (use replication/failover instead)
- Performance issues (use query optimization instead)

---

## Prerequisites

### Required Access
- [ ] PostgreSQL superuser access
- [ ] SSH/console access to database server
- [ ] Access to backup storage (S3/GCS/local)
- [ ] Access to WAL archive location

### Required Information
- [ ] Target recovery timestamp (YYYY-MM-DD HH:MM:SS TZ)
- [ ] Latest base backup before target time
- [ ] WAL archive location
- [ ] Database connection string

### Tools Needed
```bash
# PostgreSQL tools
psql --version  # Should be 13+
pg_basebackup --version
pg_waldump --version

# AWS CLI (if using S3 for backups)
aws --version
```

---

## Recovery Process

### Step 1: Assess the Situation

**Determine the target recovery point:**

```sql
-- Find when the incident occurred
SELECT * FROM property_timeline
WHERE event_type = 'property_updated'
  AND created_at > '2024-01-15 00:00:00'
ORDER BY created_at DESC
LIMIT 50;

-- Identify last known good state
-- TARGET_TIME = moment before corruption occurred
```

**Document current state:**

```bash
# Record current database size
psql -U postgres -d realestateos -c "SELECT pg_database_size('realestateos');"

# Count critical tables
psql -U postgres -d realestateos -c "
SELECT
  'properties' as table_name, COUNT(*) as row_count FROM properties
UNION ALL
SELECT
  'communications', COUNT(*) FROM communications
UNION ALL
SELECT
  'users', COUNT(*) FROM users;
"

# Save to file for comparison
psql -U postgres -d realestateos -c "..." > /tmp/pre_recovery_state.txt
```

### Step 2: Stop Application Services

**Prevent new writes to database:**

```bash
# Stop application containers
docker-compose stop api celery frontend

# Or for Kubernetes
kubectl scale deployment/api --replicas=0
kubectl scale deployment/celery-worker --replicas=0

# Verify no connections
psql -U postgres -c "
SELECT count(*)
FROM pg_stat_activity
WHERE datname = 'realestateos'
  AND state = 'active';
"
```

**Notify stakeholders:**

```bash
# Send notification (example using Slack webhook)
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"🚨 PITR in progress - database read-only mode"}' \
  $SLACK_WEBHOOK_URL
```

### Step 3: Create Current Backup (Safety Net)

**Always backup current state before recovery:**

```bash
# Create timestamped backup
BACKUP_DIR="/var/backups/postgresql"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

pg_dump -U postgres -Fc realestateos > \
  $BACKUP_DIR/pre_pitr_backup_$TIMESTAMP.dump

# Verify backup created
ls -lh $BACKUP_DIR/pre_pitr_backup_$TIMESTAMP.dump

# Calculate checksum
sha256sum $BACKUP_DIR/pre_pitr_backup_$TIMESTAMP.dump > \
  $BACKUP_DIR/pre_pitr_backup_$TIMESTAMP.dump.sha256
```

### Step 4: Identify Required Backup and WAL Files

**Find the base backup:**

```bash
# List available backups
aws s3 ls s3://realestateos-backups/base/ --recursive | grep backup

# Choose backup BEFORE target time
# Example: target = 2024-01-15 14:30:00
# Use backup from: 2024-01-15 00:00:00

BACKUP_TO_RESTORE="s3://realestateos-backups/base/2024-01-15_000000.tar.gz"
```

**Calculate required WAL files:**

```bash
# Get WAL file name for target time
# Format: 000000010000000000000001 (24 hex digits)

# Download backup label
aws s3 cp s3://realestateos-backups/base/2024-01-15_000000/backup_label /tmp/

# Find starting WAL
grep "START WAL LOCATION" /tmp/backup_label
# Example output: 000000010000000000000023

# List WAL files from start to target
aws s3 ls s3://realestateos-backups/wal/ | \
  awk '$4 >= "000000010000000000000023" && $4 <= "000000010000000000000050"'
```

### Step 5: Prepare Recovery Environment

**Create recovery directory:**

```bash
# Stop PostgreSQL
sudo systemctl stop postgresql

# Create recovery directory
sudo mkdir -p /var/lib/postgresql/recovery
sudo chown postgres:postgres /var/lib/postgresql/recovery

# Download base backup
cd /var/lib/postgresql/recovery
sudo -u postgres aws s3 cp $BACKUP_TO_RESTORE - | \
  sudo -u postgres tar -xzf -

# Create WAL archive directory
sudo -u postgres mkdir -p /var/lib/postgresql/recovery/pg_wal/archive_status
```

**Download WAL files:**

```bash
# Download all required WAL files
aws s3 sync s3://realestateos-backups/wal/ \
  /var/lib/postgresql/recovery/pg_wal/ \
  --exclude "*" \
  --include "0000000100000000000000[2-5]*"

# Verify WAL files downloaded
ls -lh /var/lib/postgresql/recovery/pg_wal/ | wc -l
```

### Step 6: Configure Recovery

**Create recovery.conf (PostgreSQL 12+: postgresql.auto.conf):**

```bash
# For PostgreSQL 12+
sudo -u postgres tee /var/lib/postgresql/recovery/postgresql.auto.conf <<EOF
# Recovery configuration
restore_command = 'cp /var/lib/postgresql/recovery/pg_wal/%f %p'
recovery_target_time = '2024-01-15 14:30:00+00'
recovery_target_action = 'promote'
EOF

# Create signal file for recovery
sudo -u postgres touch /var/lib/postgresql/recovery/recovery.signal
```

**Alternative restore_command using S3:**

```bash
restore_command = 'aws s3 cp s3://realestateos-backups/wal/%f %p'
```

### Step 7: Start Recovery

**Start PostgreSQL in recovery mode:**

```bash
# Point PostgreSQL to recovery directory (modify postgresql.conf)
sudo -u postgres vim /etc/postgresql/13/main/postgresql.conf

# Change data_directory temporarily
# data_directory = '/var/lib/postgresql/recovery'

# Start PostgreSQL
sudo systemctl start postgresql

# Monitor recovery progress
tail -f /var/log/postgresql/postgresql-13-main.log

# Look for:
# "starting point-in-time recovery to ..."
# "recovery ending at WAL..."
# "database system is ready to accept connections"
```

**Monitor recovery:**

```bash
# Check recovery status
psql -U postgres -c "SELECT pg_is_in_recovery();"

# If still recovering, check progress
psql -U postgres -c "
SELECT
  pg_last_wal_receive_lsn(),
  pg_last_wal_replay_lsn(),
  pg_last_xact_replay_timestamp();
"
```

### Step 8: Verification

**Verify data integrity:**

```sql
-- Connect to recovered database
psql -U postgres -d realestateos

-- Check row counts
SELECT
  'properties' as table_name, COUNT(*) as row_count FROM properties
UNION ALL
SELECT
  'communications', COUNT(*) FROM communications
UNION ALL
SELECT
  'users', COUNT(*) FROM users;

-- Compare with pre-recovery state
-- Should have FEWER rows than current state (rolled back)

-- Verify specific records
SELECT * FROM properties WHERE id = 12345;
SELECT * FROM communications
WHERE created_at > '2024-01-15 14:30:00';  -- Should return 0 rows

-- Check last timeline event is before target time
SELECT MAX(created_at) FROM property_timeline;
-- Should be < '2024-01-15 14:30:00'
```

**Run application health checks:**

```bash
# Start application in read-only mode first
docker-compose up -d api

# Test critical endpoints
curl -H "Authorization: Bearer $TEST_TOKEN" \
  http://localhost:8000/api/v1/health

# Check specific property
curl -H "Authorization: Bearer $TEST_TOKEN" \
  http://localhost:8000/api/v1/properties/12345
```

### Step 9: Finalize Recovery

**If verification successful:**

```bash
# 1. Replace production data directory
sudo systemctl stop postgresql

sudo mv /var/lib/postgresql/13/main /var/lib/postgresql/13/main.corrupted
sudo mv /var/lib/postgresql/recovery /var/lib/postgresql/13/main

# 2. Update postgresql.conf if needed
sudo -u postgres vim /etc/postgresql/13/main/postgresql.conf
# Ensure data_directory points to correct location

# 3. Restart PostgreSQL
sudo systemctl start postgresql

# 4. Restart application services
docker-compose up -d

# 5. Monitor logs
docker-compose logs -f api
```

**Notify stakeholders:**

```bash
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"✅ PITR completed successfully - database restored to 2024-01-15 14:30:00"}' \
  $SLACK_WEBHOOK_URL
```

---

## Verification

### Post-Recovery Checklist

- [ ] Database is accepting connections
- [ ] Row counts match expected state
- [ ] No data exists after target recovery time
- [ ] Application health checks pass
- [ ] Critical workflows function correctly
- [ ] No errors in PostgreSQL logs
- [ ] No errors in application logs
- [ ] Team notified of completion

### Data Validation Queries

```sql
-- 1. Verify timeline integrity
SELECT MIN(created_at) as earliest, MAX(created_at) as latest
FROM property_timeline;

-- 2. Check for orphaned records
SELECT COUNT(*) FROM communications c
WHERE NOT EXISTS (
  SELECT 1 FROM properties p WHERE p.id = c.property_id
);

-- 3. Verify user data
SELECT COUNT(*), MAX(created_at) FROM users;

-- 4. Check last modified times
SELECT
  relname as table_name,
  last_vacuum,
  last_autovacuum
FROM pg_stat_user_tables
ORDER BY relname;
```

---

## Troubleshooting

### Issue: WAL files not found

**Symptoms:**
```
FATAL: could not open file "pg_wal/000000010000000000000045": No such file or directory
```

**Solutions:**
```bash
# 1. Check WAL archive
ls -lh /var/lib/postgresql/recovery/pg_wal/

# 2. Download missing files
aws s3 cp s3://realestateos-backups/wal/000000010000000000000045 \
  /var/lib/postgresql/recovery/pg_wal/

# 3. Verify restore_command
psql -U postgres -c "SHOW restore_command;"
```

### Issue: Recovery target not reached

**Symptoms:**
```
LOG: recovery stopping before target time
```

**Solutions:**
```bash
# 1. Check if more WAL files needed
# May need files beyond initial estimate

# 2. Adjust recovery target
# Edit postgresql.auto.conf
recovery_target_time = '2024-01-15 15:00:00+00'  # Extend window

# 3. Check for gaps in WAL sequence
pg_waldump /var/lib/postgresql/recovery/pg_wal/000000010000000000000045
```

### Issue: Database size larger than expected

**Symptoms:**
Restored database is larger than it should be

**Solutions:**
```sql
-- Vacuum to reclaim space
VACUUM FULL ANALYZE;

-- Check for bloat
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Issue: Permissions errors

**Symptoms:**
```
ERROR: permission denied for table properties
```

**Solutions:**
```sql
-- Restore ownership
ALTER DATABASE realestateos OWNER TO realestate_user;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO realestate_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO realestate_user;
```

---

## Rollback

If recovery fails or produces unexpected results:

### Option 1: Restore from pre-PITR backup

```bash
# Stop PostgreSQL
sudo systemctl stop postgresql

# Restore from pre-PITR backup
sudo -u postgres pg_restore -U postgres -d realestateos \
  /var/backups/postgresql/pre_pitr_backup_20240115_143000.dump

# Start PostgreSQL
sudo systemctl start postgresql
```

### Option 2: Revert to original corrupted state

```bash
# Stop PostgreSQL
sudo systemctl stop postgresql

# Restore original data directory
sudo rm -rf /var/lib/postgresql/13/main
sudo mv /var/lib/postgresql/13/main.corrupted /var/lib/postgresql/13/main

# Start PostgreSQL
sudo systemctl start postgresql
```

---

## Best Practices

1. **Always test PITR in staging** before performing in production
2. **Document everything** - timestamps, commands, decisions
3. **Communicate clearly** with stakeholders throughout
4. **Verify backups regularly** - test restore monthly
5. **Monitor WAL archiving** - ensure no gaps
6. **Keep multiple backup generations** - don't rely on single backup
7. **Practice recovery procedures** - run drills quarterly

---

## Related Runbooks

- [Database Backup Procedures](./DATABASE_BACKUP.md)
- [Disaster Recovery Plan](./DISASTER_RECOVERY.md)
- [PostgreSQL Maintenance](./POSTGRESQL_MAINTENANCE.md)

---

## Revision History

| Date       | Version | Author | Changes |
|------------|---------|--------|---------|
| 2024-01-15 | 1.0     | DevOps | Initial version |

---

## Emergency Contacts

- **Database Team**: db-team@example.com
- **DevOps On-Call**: oncall@example.com
- **Slack Channel**: #database-emergencies
- **PagerDuty**: https://example.pagerduty.com
