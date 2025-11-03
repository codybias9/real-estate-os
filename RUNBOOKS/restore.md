# Disaster Recovery: Restore Procedures

## Quick Reference

| Scenario | RTO | RPO | Procedure |
|----------|-----|-----|-----------|
| Accidental table drop | 15 min | < 5 min | [PITR Restore](#pitr-restore) |
| Database corruption | 30 min | < 5 min | [Full Restore](#full-database-restore) |
| Deleted memo file | 5 min | 0 | [MinIO Object Restore](#minio-object-restore) |
| Complete site failure | 2 hours | < 5 min | [Full DR Failover](#full-disaster-recovery) |

---

## 1. Point-in-Time Recovery (PITR)

**Use Case**: Restore database to a specific point in time before an incident.

**Example**: Table was accidentally dropped at 14:35 UTC. Restore to 14:30 UTC (5 minutes before).

### Prerequisites

- [ ] pgBackRest configured and backups available
- [ ] WAL archives available for target time
- [ ] Postgres service stopped
- [ ] Ops team notified

### Step 1: Identify Target Recovery Time

```bash
# Check recent activity to determine restore point
psql -h localhost -U realestate_app -d realestate -c "
SELECT
    schemaname,
    tablename,
    last_vacuum,
    last_autovacuum,
    last_analyze
FROM pg_stat_user_tables
ORDER BY last_analyze DESC
LIMIT 10;"
```

**Decision Point**: Determine exact timestamp to restore to (format: `YYYY-MM-DD HH:MM:SS`).

### Step 2: Stop PostgreSQL

```bash
# Stop application services first to prevent new connections
sudo systemctl stop realestate-api
sudo systemctl stop realestate-workers

# Stop PostgreSQL
sudo systemctl stop postgresql

# Verify stopped
sudo systemctl status postgresql
```

### Step 3: Backup Current State (Safety)

```bash
# Move current data directory to backup location
sudo mv /var/lib/postgresql/14/main /var/lib/postgresql/14/main.backup.$(date +%Y%m%d-%H%M%S)

# Create new empty directory
sudo mkdir -p /var/lib/postgresql/14/main
sudo chown postgres:postgres /var/lib/postgresql/14/main
```

### Step 4: Execute PITR Restore

```bash
# Restore to specific point in time
sudo -u postgres pgbackrest \
    --stanza=realestate-db \
    --type=time \
    --target="2025-11-03 14:30:00" \
    --target-action=promote \
    --delta \
    restore

# Check for errors
echo $?  # Should be 0
```

**Expected Output**:
```
P00   INFO: restore command begin 2.48
P00   INFO: restore backup set 20251103-020000F
P00   INFO: restore file /var/lib/postgresql/14/main/base/...
P00   INFO: restore command end: completed successfully (123s)
```

### Step 5: Start PostgreSQL and Verify

```bash
# Start PostgreSQL
sudo systemctl start postgresql

# Wait for startup
sleep 10

# Verify recovery
sudo -u postgres psql -c "SELECT pg_is_in_recovery();"
# Should return: f (false, meaning recovery is complete)

# Check restored data
sudo -u postgres psql -d realestate -c "
SELECT
    NOW() as current_time,
    (SELECT MAX(created_at) FROM properties) as last_property,
    (SELECT MAX(state_changed_at) FROM pipeline_state) as last_state_change;
"

# Verify table counts
sudo -u postgres psql -d realestate -c "
SELECT 'properties' as table, COUNT(*) FROM properties
UNION ALL
SELECT 'pipeline_state', COUNT(*) FROM pipeline_state
UNION ALL
SELECT 'timeline_entries', COUNT(*) FROM timeline_entries;
"
```

### Step 6: Validate Application Health

```bash
# Start application services
sudo systemctl start realestate-api
sudo systemctl start realestate-workers

# Health check
curl http://localhost:8000/health

# Verify recent API operations
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/properties?limit=10
```

### Step 7: Document Restore

```bash
# Create restore report
cat > /var/log/restore-report-$(date +%Y%m%d-%H%M%S).txt <<EOF
Restore Type: Point-in-Time Recovery (PITR)
Date: $(date)
Operator: $(whoami)
Target Time: 2025-11-03 14:30:00
Backup Set: 20251103-020000F
Duration: 123s
Status: SUCCESS
Verification:
  - Postgres started: OK
  - Table counts: VERIFIED
  - API health check: PASSED
  - Last property: 2025-11-03 14:29:45
EOF

# Upload to S3
aws s3 cp /var/log/restore-report-* s3://realestate-ops/restore-reports/
```

### Rollback (If Restore Failed)

```bash
# Stop Postgres
sudo systemctl stop postgresql

# Restore original data directory
sudo rm -rf /var/lib/postgresql/14/main
sudo mv /var/lib/postgresql/14/main.backup.* /var/lib/postgresql/14/main

# Start Postgres
sudo systemctl start postgresql
```

---

## 2. Full Database Restore

**Use Case**: Restore entire database from latest backup (no PITR needed).

**Example**: Database corruption detected, restore from last night's full backup.

### Prerequisites

- [ ] Latest backup verified
- [ ] Postgres service stopped
- [ ] Incident ticket created
- [ ] Ops team notified

### Step 1: Stop Services

```bash
sudo systemctl stop realestate-api
sudo systemctl stop realestate-workers
sudo systemctl stop postgresql
```

### Step 2: Check Available Backups

```bash
sudo -u postgres pgbackrest --stanza=realestate-db info
```

**Expected Output**:
```
stanza: realestate-db
    status: ok
    cipher: aes-256-cbc

    db (current)
        wal archive min/max (14): 000000010000000000000001/00000001000000000000001F

        full backup: 20251103-020000F
            timestamp start/stop: 2025-11-03 02:00:00 / 2025-11-03 02:08:45
            wal start/stop: 000000010000000000000010 / 000000010000000000000012
            database size: 48.2GB, database backup size: 48.2GB
            repo1: backup size: 12.1GB
```

### Step 3: Execute Full Restore

```bash
# Restore latest backup
sudo -u postgres pgbackrest \
    --stanza=realestate-db \
    --delta \
    restore

# Verify
echo $?  # Should be 0
```

### Step 4: Start and Verify

```bash
# Start PostgreSQL
sudo systemctl start postgresql

# Verify
sudo -u postgres psql -d realestate -c "
SELECT
    NOW() as current_time,
    pg_database_size('realestate') as db_size,
    COUNT(*) as table_count
FROM information_schema.tables
WHERE table_schema = 'public';
"
```

### Step 5: Run Data Validation

```bash
# Create validation script
cat > /tmp/validate_restore.sql <<EOF
-- Validate restore integrity
DO \$\$
DECLARE
    property_count INT;
    pipeline_count INT;
    timeline_count INT;
    recent_activity TIMESTAMP;
BEGIN
    -- Count checks
    SELECT COUNT(*) INTO property_count FROM properties;
    SELECT COUNT(*) INTO pipeline_count FROM pipeline_state;
    SELECT COUNT(*) INTO timeline_count FROM timeline_entries;

    -- Recent activity check
    SELECT MAX(created_at) INTO recent_activity FROM timeline_entries;

    -- Report
    RAISE NOTICE 'Properties: %', property_count;
    RAISE NOTICE 'Pipeline states: %', pipeline_count;
    RAISE NOTICE 'Timeline entries: %', timeline_count;
    RAISE NOTICE 'Last activity: %', recent_activity;

    -- Validate
    IF property_count = 0 THEN
        RAISE EXCEPTION 'VALIDATION FAILED: No properties found';
    END IF;

    IF recent_activity < NOW() - INTERVAL '7 days' THEN
        RAISE WARNING 'Last activity is older than 7 days';
    END IF;

    RAISE NOTICE 'VALIDATION PASSED';
END;
\$\$;
EOF

# Run validation
sudo -u postgres psql -d realestate -f /tmp/validate_restore.sql
```

---

## 3. MinIO Object Restore

**Use Case**: Restore deleted or corrupted object from MinIO.

**Example**: Memo PDF accidentally deleted, restore from versioning.

### Prerequisites

- [ ] MinIO versioning enabled
- [ ] Object path known
- [ ] Deletion timestamp known

### Step 1: List Object Versions

```bash
# List all versions of an object
mc ls --versions myminio/realestate-memos/memos/prop-12345/memo.pdf
```

**Expected Output**:
```
[2025-11-03 14:35:22 EST]   1.2MiB v3 memo.pdf (DELETE marker)
[2025-11-03 10:15:10 EST]   1.2MiB v2 memo.pdf
[2025-11-02 16:22:33 EST]   1.1MiB v1 memo.pdf
```

### Step 2: Restore Specific Version

```bash
# Method 1: Copy previous version to new object
mc cp --vid v2 \
  myminio/realestate-memos/memos/prop-12345/memo.pdf \
  myminio/realestate-memos/memos/prop-12345/memo-restored.pdf

# Method 2: Remove delete marker to restore
mc rm --vid v3 myminio/realestate-memos/memos/prop-12345/memo.pdf

# Verify restoration
mc stat myminio/realestate-memos/memos/prop-12345/memo.pdf
```

### Step 3: Verify Object Integrity

```bash
# Download and verify checksum
mc cat myminio/realestate-memos/memos/prop-12345/memo.pdf | sha256sum

# Compare with original hash (if available)
# Expected: matching hash confirms integrity

# Verify file is valid PDF
file <(mc cat myminio/realestate-memos/memos/prop-12345/memo.pdf)
# Expected: PDF document, version 1.7
```

### Step 4: Document Restore

```bash
# Create restore log
cat > /home/user/real-estate-os/audit_artifacts/logs/minio-restore-$(date +%Y%m%d-%H%M%S).txt <<EOF
Object Restore Report
Date: $(date)
Operator: $(whoami)
Object Path: myminio/realestate-memos/memos/prop-12345/memo.pdf
Restored Version: v2
Original Size: 1.2MiB
Status: SUCCESS
Verification:
  - Object accessible: YES
  - Checksum match: VERIFIED
  - File type: PDF
EOF
```

---

## 4. MinIO Bucket Mirror Restore

**Use Case**: Restore entire bucket from secondary site or backup.

### Step 1: Verify Backup Bucket

```bash
# Check backup bucket exists
mc ls s3backup/realestate-memos/
```

### Step 2: Mirror Restore

```bash
# Mirror backup to primary
mc mirror s3backup/realestate-memos/ myminio/realestate-memos/

# Compare object counts
echo "Backup bucket:"
mc du s3backup/realestate-memos/

echo "Primary bucket:"
mc du myminio/realestate-memos/
```

### Step 3: Verify Objects

```bash
# Verify random sample of objects
mc ls myminio/realestate-memos/ | shuf | head -10 | while read line; do
    file=$(echo $line | awk '{print $NF}')
    mc stat myminio/realestate-memos/$file
done
```

---

## 5. Full Disaster Recovery

**Use Case**: Complete site failure, restore entire system.

### Prerequisites

- [ ] Secondary site available
- [ ] DNS ready to update
- [ ] Backups verified
- [ ] Incident commander assigned
- [ ] Stakeholders notified

### DR Checklist

```bash
#!/bin/bash
# Full DR restore script
# Run with: sudo bash dr-restore.sh

set -e

echo "========================================="
echo "DISASTER RECOVERY RESTORE"
echo "========================================="
echo "Start time: $(date)"

# 1. Restore PostgreSQL
echo "[1/5] Restoring PostgreSQL..."
sudo -u postgres pgbackrest --stanza=realestate-db --delta restore
sudo systemctl start postgresql
echo "PostgreSQL: OK"

# 2. Restore MinIO buckets
echo "[2/5] Restoring MinIO objects..."
mc mirror s3backup/realestate-memos/ myminio/realestate-memos/
mc mirror s3backup/realestate-documents/ myminio/realestate-documents/
echo "MinIO: OK"

# 3. Restore application config
echo "[3/5] Restoring application configuration..."
aws s3 cp s3://realestate-ops/config/prod/ /etc/realestate/ --recursive
echo "Config: OK"

# 4. Start application services
echo "[4/5] Starting application services..."
sudo systemctl start realestate-api
sudo systemctl start realestate-workers
sudo systemctl start realestate-timeline
echo "Services: STARTED"

# 5. Validate
echo "[5/5] Validating restore..."
sleep 10

# Health check
curl -f http://localhost:8000/health || { echo "Health check FAILED"; exit 1; }

# Database check
psql -h localhost -U realestate_app -d realestate -c "SELECT COUNT(*) FROM properties;" || { echo "DB check FAILED"; exit 1; }

# MinIO check
mc stat myminio/realestate-memos/ || { echo "MinIO check FAILED"; exit 1; }

echo "========================================="
echo "DISASTER RECOVERY COMPLETE"
echo "End time: $(date)"
echo "========================================="

# Generate report
cat > /var/log/dr-restore-$(date +%Y%m%d-%H%M%S).log <<EOF
Disaster Recovery Restore Report
Date: $(date)
Duration: $SECONDS seconds
Components Restored:
  - PostgreSQL: SUCCESS
  - MinIO: SUCCESS
  - Application Config: SUCCESS
  - Services: STARTED
  - Validation: PASSED
EOF
```

---

## 6. Restore Test Verification

**Frequency**: Weekly (automated)
**Last Verified**: {{date}}
**Next Test**: {{date + 7 days}}

### Automated Restore Test

```bash
#!/bin/bash
# Weekly automated restore test
# Cron: 0 4 * * 0 (Sunday 04:00 UTC)

STAGING_DIR="/var/lib/postgresql/staging"
REPORT_FILE="/home/user/real-estate-os/audit_artifacts/logs/restore-test-$(date +%Y%m%d).txt"

echo "Automated Restore Test: $(date)" | tee $REPORT_FILE

# Stop staging
sudo systemctl stop postgresql-staging

# Restore latest backup to staging
sudo -u postgres pgbackrest \
    --stanza=realestate-db \
    --pg1-path=$STAGING_DIR \
    --delta \
    restore 2>&1 | tee -a $REPORT_FILE

# Start staging
sudo systemctl start postgresql-staging

# Wait for startup
sleep 10

# Validation queries
sudo -u postgres psql -h localhost -p 5433 -d realestate_staging <<EOF | tee -a $REPORT_FILE
-- Row counts
\echo 'TABLE COUNTS:'
SELECT 'properties' as table, COUNT(*) as count FROM properties
UNION ALL
SELECT 'pipeline_state', COUNT(*) FROM pipeline_state
UNION ALL
SELECT 'timeline_entries', COUNT(*) FROM timeline_entries
ORDER BY table;

-- Recent activity
\echo '\nRECENT ACTIVITY:'
SELECT
    'Last property' as metric,
    MAX(created_at)::text as value
FROM properties
UNION ALL
SELECT
    'Last state change',
    MAX(state_changed_at)::text
FROM pipeline_state;

-- Index integrity
\echo '\nINDEX INTEGRITY:'
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
EOF

# Performance test
echo "\nPERFORMANCE TEST:" | tee -a $REPORT_FILE
time sudo -u postgres psql -h localhost -p 5433 -d realestate_staging -c "
EXPLAIN ANALYZE
SELECT p.*, ps.stage, ps.score
FROM properties p
JOIN pipeline_state ps ON p.id = ps.property_id
WHERE ps.stage = 'qualified'
LIMIT 100;
" 2>&1 | tee -a $REPORT_FILE

# Save results
echo "\nTest Complete: $(date)" | tee -a $REPORT_FILE

# Upload to S3
aws s3 cp $REPORT_FILE s3://realestate-ops/restore-tests/

# Generate artifact for audit
cp $REPORT_FILE /home/user/real-estate-os/audit_artifacts/logs/restore-proof.txt

echo "Report saved: $REPORT_FILE"
```

---

## 7. Emergency Contacts

| Role | Name | Phone | Email |
|------|------|-------|-------|
| Incident Commander | On-Call Ops | +1-555-0100 | ops@realestate.io |
| DBA | Database Team | +1-555-0101 | dba@realestate.io |
| DevOps Lead | Platform Team | +1-555-0102 | devops@realestate.io |
| AWS Support | Enterprise | 1-800-AWS-SUPPORT | - |

---

## 8. Common Issues & Troubleshooting

### Issue: WAL Archives Missing

**Symptom**: PITR fails with "WAL archive not found"

**Solution**:
```bash
# Check WAL archive status
sudo -u postgres pg_archivecleanup -n /var/lib/postgresql/14/archive/ 000000010000000000000001

# If WAL is missing, restore to last available full/diff backup
sudo -u postgres pgbackrest --stanza=realestate-db --type=immediate restore
```

### Issue: Restore Timeout

**Symptom**: Restore takes > 1 hour

**Solution**:
```bash
# Increase process-max for parallel restore
sudo -u postgres pgbackrest \
    --stanza=realestate-db \
    --process-max=8 \
    --delta \
    restore
```

### Issue: MinIO Object Not Found

**Symptom**: Object version doesn't exist

**Solution**:
```bash
# Check lifecycle policy hasn't expired versions
mc ilm ls myminio/realestate-memos

# Check replication lag
mc replicate status myminio/realestate-memos

# Restore from S3 backup if versioning expired
aws s3 cp s3://realestate-backup/memos/... myminio/realestate-memos/...
```

---

## Appendix: Verification Artifacts

All restore operations must generate artifacts in:
```
/home/user/real-estate-os/audit_artifacts/logs/
├── restore-proof.txt          # Latest weekly restore test
├── restore-steps.txt          # Detailed restore commands
├── postgres-pitr-YYYYMMDD.txt # PITR restore logs
├── minio-restore-YYYYMMDD.txt # Object restore logs
└── dr-restore-YYYYMMDD.log    # Full DR restore logs
```

Screenshot evidence in:
```
/home/user/real-estate-os/audit_artifacts/ui/
├── restore-proof.png          # Grafana dashboard during restore
├── postgres-restored.png      # PostgreSQL after restore
└── minio-versioning.png       # MinIO versioning enabled
```

---

**Last Updated**: 2025-11-03
**Last Verified**: 2025-11-03
**Next Review**: 2025-12-01
**Owner**: DevOps Team
