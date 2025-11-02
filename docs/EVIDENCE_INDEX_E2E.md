# Evidence Artifact Index

**Audit Date**: 2025-11-02
**Total Artifacts**: 35 (7 created, 28 required but not created due to missing infrastructure)

---

## Created Artifacts ✅

### Repository Mapping
| Artifact | Path | Description | Status |
|----------|------|-------------|--------|
| File Tree | `/artifacts/repo/tree.txt` | Complete file inventory (239 files) | ✅ Created |
| LOC Stats | `/artifacts/repo/loc-by-folder.csv` | Lines of code by directory | ✅ Created |

### Database
| Artifact | Path | Description | Status |
|----------|------|-------------|--------|
| Migrations List | `/artifacts/db/migrations-list.txt` | 3 migration files | ✅ Created |
| RLS Policies | `/artifacts/db/rls-policies-excerpt.txt` | Row-level security policy definitions | ✅ Created |

### API
| Artifact | Path | Description | Status |
|----------|------|-------------|--------|
| Route Inventory | `/artifacts/api/route-inventory.csv` | 71 API endpoints across 14 routers | ✅ Created |

### Data Pipelines
| Artifact | Path | Description | Status |
|----------|------|-------------|--------|
| DAG Inventory | `/artifacts/dags/inventory.csv` | 17 DAGs classified (7 real, 4 minimal, 6 stubs) | ✅ Created |

### Testing
| Artifact | Path | Description | Status |
|----------|------|-------------|--------|
| Test Files | `/artifacts/tests/test-files.txt` | 9 test files, 126 test methods | ✅ Created |

---

## Not Created - Infrastructure Not Deployed ❌

### Database (Not Deployed)
| Artifact | Path | Reason Not Created |
|----------|------|-------------------|
| Migration Apply Log | `/artifacts/db/apply-log.txt` | No PostgreSQL instance to apply migrations to |
| RLS Explain Plan | `/artifacts/isolation/rls-explain.txt` | No database to query `SHOW POLICIES` |
| Cross-Tenant Test | `/artifacts/isolation/negative-tests-db.txt` | No database to test isolation |

### API (Not Running)
| Artifact | Path | Reason Not Created |
|----------|------|-------------------|
| OpenAPI Schema | `/artifacts/api/openapi.json` | No running FastAPI server to generate schema |
| Smoke Test Results | `/artifacts/api/smoke-results.txt` | No API to test |
| API Isolation Test | `/artifacts/isolation/negative-tests-api.txt` | No API to test cross-tenant access |

### Vector Database (Not Deployed)
| Artifact | Path | Reason Not Created |
|----------|------|-------------------|
| Qdrant Filter Proof | `/artifacts/isolation/qdrant-filter-proof.json` | No Qdrant instance deployed |

### Object Storage (Not Deployed)
| Artifact | Path | Reason Not Created |
|----------|------|-------------------|
| MinIO Prefix Test | `/artifacts/isolation/minio-prefix-proof.txt` | No MinIO instance deployed |

### Data Pipelines (Airflow Not Running)
| Artifact | Path | Reason Not Created |
|----------|------|-------------------|
| E2E Pipeline Log | `/artifacts/dags/e2e-run-log.txt` | Airflow not running, cannot execute DAGs |
| Hazard ETL Output | `/artifacts/hazards/property-<ID>-hazard-attrs.json` | Pipeline not executed |
| Provenance Output | `/artifacts/provenance/property-<ID>-provenance.json` | Pipeline not executed |
| Score Output | `/artifacts/score/subject-<ID>-score.json` | Pipeline not executed |

### Data Quality (GX Not Executed)
| Artifact | Path | Reason Not Created |
|----------|------|-------------------|
| Data Docs HTML | `/artifacts/data-quality/data-docs-index.html` | Great Expectations not run |
| Failing Checkpoint | `/artifacts/data-quality/failing-checkpoint.log` | No GX execution with failing data |
| Checkpoint Config | `/artifacts/data-quality/checkpoint-config.yaml` | No GX project initialized |

### Lineage (Marquez Not Deployed)
| Artifact | Path | Reason Not Created |
|----------|------|-------------------|
| DAG Visualization | `/artifacts/lineage/marquez-dag-run-<date>.png` | Marquez not deployed |
| Lineage Event | `/artifacts/lineage/lineage-event-sample.json` | No pipeline execution to emit events |

### ML Systems (Models Not Trained)
| Artifact | Path | Reason Not Created |
|----------|------|-------------------|
| Model Inventory | `/artifacts/ml/models-inventory.csv` | No trained artifacts exist |
| Comp Backtests | `/artifacts/comps/backtest-metrics.csv` | Backtests not executed |
| DCF MF Output | `/artifacts/dcf/golden-mf-output.json` | Not executed with real data |
| DCF CRE Output | `/artifacts/dcf/golden-cre-output.json` | Not executed with real data |
| SHAP Sample | `/artifacts/ml/shap-sample.json` | Explainability not run |
| DiCE Sample | `/artifacts/ml/dice-sample.json` | Explainability not run |
| Feast Online Trace | `/artifacts/feast/online-trace-DEMO123.json` | Feast not deployed |
| Feast Performance | `/artifacts/feast/offline-vs-online.csv` | Feast not deployed |

### Observability (Not Deployed)
| Artifact | Path | Reason Not Created |
|----------|------|-------------------|
| Grafana Dashboards | `/artifacts/observability/grafana-dashboards.json` | Grafana not deployed |
| Prometheus Targets | `/artifacts/observability/prom-targets.png` | Prometheus not deployed |
| Sentry Test Event | `/artifacts/observability/sentry-test-event.txt` | Sentry not configured |

### Performance (Not Tested)
| Artifact | Path | Reason Not Created |
|----------|------|-------------------|
| Load Scenarios | `/artifacts/perf/load-scenarios.md` | No load tests designed or run |
| p95 Results | `/artifacts/perf/latency-snapshots.csv` | No load tests run |
| Chaos Log | `/artifacts/perf/vector-chaos-log.txt` | No chaos testing performed |

### CI/CD (Not Configured)
| Artifact | Path | Reason Not Created |
|----------|------|-------------------|
| Workflows List | `/artifacts/ci/workflows-list.txt` | No GitHub Actions workflows exist |
| CI Run Logs | `/artifacts/ci/last-run-logs.txt` | No CI configured |
| Test Summary | `/artifacts/tests/test-summary.txt` | Tests not executed with pytest |

---

## Audit Scripts

Re-runnable verification scripts created:

| Script | Path | Purpose |
|--------|------|---------|
| Count LOC | `/scripts/audit/count_loc.sh` | Count lines of code by directory |
| Inventory Endpoints | `/scripts/audit/inventory_api_endpoints.py` | Extract all API endpoint definitions |
| Classify DAGs | `/scripts/audit/classify_dags.sh` | Categorize pipelines as real/stub |

---

## How to Reproduce This Audit

1. **Repository Mapping**:
   ```bash
   bash /scripts/audit/count_loc.sh
   python3 /scripts/audit/inventory_api_endpoints.py
   bash /scripts/audit/classify_dags.sh
   ```

2. **Deploy Infrastructure** (required for remaining artifacts):
   ```bash
   docker-compose up -d postgres
   docker-compose up -d redis
   docker-compose up -d airflow
   # Apply migrations
   psql -h localhost -U postgres -f db/migrations/001_create_base_schema_with_rls.sql
   ```

3. **Run API**:
   ```bash
   uvicorn api.main:app --host 0.0.0.0 --port 8000
   # Then access http://localhost:8000/docs for OpenAPI
   ```

4. **Execute Tests**:
   ```bash
   pytest tests/ --cov=. --cov-report=html
   ```

5. **Run DAG**:
   ```bash
   airflow dags test minimal_e2e_pipeline 2025-11-02
   ```

6. **Generate GX Data Docs**:
   ```bash
   great_expectations checkpoint run properties_checkpoint
   great_expectations docs build
   ```

---

## Summary

- **7 artifacts created** from code inspection
- **28 artifacts blocked** by missing infrastructure
- **All audit scripts saved** for repeatability
- **Clear path to completion** once services deployed

To complete this audit with 100% artifact coverage:
1. Deploy infrastructure (PostgreSQL, Redis, Airflow, Qdrant, Neo4j, MinIO)
2. Run services (API, Prometheus, Grafana, Marquez)
3. Execute tests and pipelines
4. Generate all 28 missing artifacts
5. Update this index with ✅ markers
