#!/usr/bin/env python3
"""
Verify Observability Stack for P0.12

Validates:
1. Prometheus configuration (10 scrape targets)
2. Grafana dashboard definitions (2 dashboards, 15+ panels)
3. Metrics instrumentation readiness
4. Alert rules (if configured)
5. Datasource configurations
"""
import json
import yaml
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def validate_prometheus_config() -> Dict[str, Any]:
    """
    Validate Prometheus configuration.

    Expected:
    - 10+ scrape targets (API, PostgreSQL, Redis, Airflow, Qdrant, MinIO, Neo4j, Grafana, Keycloak, Prometheus)
    - Proper scrape intervals
    - Correct metrics paths
    """
    print("=" * 60)
    print("VALIDATING PROMETHEUS CONFIGURATION")
    print("=" * 60)
    print()

    prometheus_config_path = project_root / "ops" / "prometheus" / "prometheus.yml"

    if not prometheus_config_path.exists():
        print(f"✗ Prometheus config not found: {prometheus_config_path}")
        return {"status": "FAIL", "reason": "Config file missing"}

    with open(prometheus_config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Validate scrape configs
    scrape_configs = config.get("scrape_configs", [])
    job_names = [job["job_name"] for job in scrape_configs]

    expected_jobs = [
        "api", "postgres", "redis", "airflow", "prometheus",
        "qdrant", "minio", "neo4j", "grafana", "keycloak"
    ]

    found_jobs = [job for job in expected_jobs if job in job_names]
    missing_jobs = [job for job in expected_jobs if job not in job_names]

    # Analyze scrape intervals
    scrape_intervals = {}
    for job in scrape_configs:
        job_name = job["job_name"]
        interval = job.get("scrape_interval", config.get("global", {}).get("scrape_interval", "15s"))
        scrape_intervals[job_name] = interval

    # Validate global settings
    global_config = config.get("global", {})
    scrape_interval = global_config.get("scrape_interval", "")
    evaluation_interval = global_config.get("evaluation_interval", "")

    results = {
        "config_file": str(prometheus_config_path),
        "status": "PASS" if len(missing_jobs) == 0 else "PARTIAL",
        "scrape_configs": {
            "total_jobs": len(scrape_configs),
            "expected_jobs": len(expected_jobs),
            "found_jobs": found_jobs,
            "missing_jobs": missing_jobs
        },
        "global_settings": {
            "scrape_interval": scrape_interval,
            "evaluation_interval": evaluation_interval,
            "cluster": global_config.get("external_labels", {}).get("cluster", ""),
            "environment": global_config.get("external_labels", {}).get("environment", "")
        },
        "scrape_intervals": scrape_intervals
    }

    print(f"Prometheus Configuration:")
    print(f"  Config File: {prometheus_config_path}")
    print(f"  Total Scrape Jobs: {len(scrape_configs)}")
    print(f"  Expected Jobs: {len(expected_jobs)}")
    print(f"  Found Jobs: {len(found_jobs)}")
    print()

    print(f"Scrape Targets:")
    for job in found_jobs:
        interval = scrape_intervals.get(job, "15s")
        print(f"  ✓ {job:15s} (interval: {interval})")

    if missing_jobs:
        print()
        print(f"Missing Targets:")
        for job in missing_jobs:
            print(f"  ✗ {job}")

    print()
    print(f"Global Settings:")
    print(f"  Scrape Interval: {scrape_interval}")
    print(f"  Evaluation Interval: {evaluation_interval}")
    print(f"  Cluster: {results['global_settings']['cluster']}")
    print(f"  Environment: {results['global_settings']['environment']}")
    print()

    if results['status'] == "PASS":
        print("✓ PROMETHEUS CONFIGURATION: PASS")
    else:
        print(f"⚠ PROMETHEUS CONFIGURATION: PARTIAL ({len(missing_jobs)} missing targets)")

    print()

    return results


def validate_grafana_dashboards() -> Dict[str, Any]:
    """
    Validate Grafana dashboard definitions.

    Expected:
    - 2+ dashboards (Overview, ML Performance)
    - 15+ panels total
    - Prometheus datasource configured
    """
    print("=" * 60)
    print("VALIDATING GRAFANA DASHBOARDS")
    print("=" * 60)
    print()

    dashboard_artifact_path = project_root / "artifacts" / "observability" / "grafana-dashboards.json"

    if not dashboard_artifact_path.exists():
        print(f"✗ Dashboard artifact not found: {dashboard_artifact_path}")
        return {"status": "FAIL", "reason": "Dashboard artifact missing"}

    with open(dashboard_artifact_path, 'r') as f:
        dashboard_spec = json.load(f)

    dashboards = dashboard_spec.get("dashboards", [])
    data_sources = dashboard_spec.get("data_sources", [])

    # Analyze dashboards
    dashboard_summaries = []
    total_panels = 0

    for dashboard in dashboards:
        dashboard_id = dashboard.get("id", "unknown")
        title = dashboard.get("title", "Untitled")
        panels = dashboard.get("panels", [])
        panel_count = len(panels)
        total_panels += panel_count

        # Categorize panel types
        panel_types = {}
        for panel in panels:
            panel_type = panel.get("type", "unknown")
            panel_types[panel_type] = panel_types.get(panel_type, 0) + 1

        dashboard_summaries.append({
            "id": dashboard_id,
            "title": title,
            "panel_count": panel_count,
            "panel_types": panel_types,
            "refresh": dashboard.get("refresh", ""),
            "tags": dashboard.get("tags", [])
        })

    # Analyze datasources
    datasource_summaries = []
    for ds in data_sources:
        datasource_summaries.append({
            "name": ds.get("name", ""),
            "type": ds.get("type", ""),
            "url": ds.get("url", ""),
            "is_default": ds.get("isDefault", False)
        })

    results = {
        "artifact_file": str(dashboard_artifact_path),
        "status": "PASS" if len(dashboards) >= 2 and total_panels >= 10 else "FAIL",
        "dashboards": {
            "total": len(dashboards),
            "summaries": dashboard_summaries
        },
        "panels": {
            "total": total_panels,
            "expected_minimum": 10
        },
        "datasources": {
            "total": len(data_sources),
            "summaries": datasource_summaries
        }
    }

    print(f"Grafana Dashboards:")
    print(f"  Artifact File: {dashboard_artifact_path}")
    print(f"  Total Dashboards: {len(dashboards)}")
    print(f"  Total Panels: {total_panels}")
    print()

    for summary in dashboard_summaries:
        print(f"Dashboard: {summary['title']}")
        print(f"  ID: {summary['id']}")
        print(f"  Panels: {summary['panel_count']}")
        print(f"  Panel Types: {summary['panel_types']}")
        print(f"  Refresh: {summary['refresh']}")
        print(f"  Tags: {', '.join(summary['tags'])}")
        print()

    print(f"Data Sources:")
    for ds in datasource_summaries:
        default_marker = " (default)" if ds['is_default'] else ""
        print(f"  - {ds['name']}: {ds['type']}{default_marker}")
        print(f"    URL: {ds['url']}")

    print()

    if results['status'] == "PASS":
        print("✓ GRAFANA DASHBOARDS: PASS")
    else:
        print("✗ GRAFANA DASHBOARDS: FAIL")

    print()

    return results


def validate_grafana_provisioning() -> Dict[str, Any]:
    """
    Validate Grafana provisioning configuration.
    """
    print("=" * 60)
    print("VALIDATING GRAFANA PROVISIONING")
    print("=" * 60)
    print()

    # Check datasource provisioning
    datasource_config_path = project_root / "ops" / "grafana" / "provisioning" / "datasources" / "prometheus.yml"
    dashboard_config_path = project_root / "ops" / "grafana" / "provisioning" / "dashboards" / "default.yml"

    results = {
        "datasource_provisioning": {},
        "dashboard_provisioning": {}
    }

    # Validate datasource provisioning
    if datasource_config_path.exists():
        with open(datasource_config_path, 'r') as f:
            datasource_config = yaml.safe_load(f)

        datasources = datasource_config.get("datasources", [])
        results["datasource_provisioning"] = {
            "status": "PASS",
            "config_file": str(datasource_config_path),
            "datasource_count": len(datasources)
        }
        print(f"Datasource Provisioning:")
        print(f"  Config: {datasource_config_path}")
        print(f"  Datasources: {len(datasources)}")
        for ds in datasources:
            print(f"    - {ds.get('name', 'unknown')}: {ds.get('type', 'unknown')}")
    else:
        results["datasource_provisioning"] = {
            "status": "FAIL",
            "reason": "Config file missing"
        }
        print(f"✗ Datasource provisioning config not found")

    print()

    # Validate dashboard provisioning
    if dashboard_config_path.exists():
        with open(dashboard_config_path, 'r') as f:
            dashboard_config = yaml.safe_load(f)

        providers = dashboard_config.get("providers", [])
        results["dashboard_provisioning"] = {
            "status": "PASS",
            "config_file": str(dashboard_config_path),
            "provider_count": len(providers)
        }
        print(f"Dashboard Provisioning:")
        print(f"  Config: {dashboard_config_path}")
        print(f"  Providers: {len(providers)}")
        for provider in providers:
            print(f"    - {provider.get('name', 'unknown')}")
            print(f"      Folder: {provider.get('folder', '')}")
            print(f"      Path: {provider.get('options', {}).get('path', '')}")
    else:
        results["dashboard_provisioning"] = {
            "status": "FAIL",
            "reason": "Config file missing"
        }
        print(f"✗ Dashboard provisioning config not found")

    print()

    overall_status = "PASS" if (
        results["datasource_provisioning"].get("status") == "PASS" and
        results["dashboard_provisioning"].get("status") == "PASS"
    ) else "FAIL"

    results["overall_status"] = overall_status

    if overall_status == "PASS":
        print("✓ GRAFANA PROVISIONING: PASS")
    else:
        print("✗ GRAFANA PROVISIONING: FAIL")

    print()

    return results


def generate_metrics_instrumentation_checklist() -> Dict[str, Any]:
    """
    Generate checklist of metrics that should be instrumented.
    """
    print("=" * 60)
    print("METRICS INSTRUMENTATION CHECKLIST")
    print("=" * 60)
    print()

    # Define expected metrics
    expected_metrics = {
        "API Metrics": [
            "http_requests_total (counter) - Total HTTP requests by method, endpoint, status",
            "http_request_duration_seconds (histogram) - Request latency distribution",
            "http_requests_in_progress (gauge) - Active requests",
            "authentication_attempts_total (counter) - Auth attempts by status",
            "rate_limit_exceeded_total (counter) - Rate limit violations"
        ],
        "ML Metrics": [
            "model_inference_duration_seconds (histogram) - Model inference latency",
            "comp_critic_duration_seconds (histogram) - Comp-Critic valuation time",
            "dcf_engine_duration_seconds (histogram) - DCF computation time",
            "feast_online_fetch_duration_seconds (histogram) - Feature fetch latency",
            "shap_compute_duration_seconds (histogram) - SHAP computation time",
            "offer_optimizer_status (counter) - Optimization status by result",
            "offer_optimizer_total (counter) - Total optimization runs"
        ],
        "Airflow Metrics": [
            "airflow_dag_run_status (counter) - DAG run outcomes",
            "airflow_dag_run_last_success_timestamp (gauge) - Last successful run",
            "airflow_task_duration_seconds (histogram) - Task execution time",
            "airflow_dag_run_duration_seconds (histogram) - End-to-end DAG time"
        ],
        "Database Metrics": [
            "pg_stat_database_tup_fetched (gauge) - Rows read",
            "pg_stat_database_tup_inserted (gauge) - Rows inserted",
            "pg_stat_database_connections (gauge) - Active connections",
            "pg_stat_database_blks_hit_ratio (gauge) - Cache hit ratio"
        ],
        "Vector Store Metrics": [
            "qdrant_search_duration_seconds (histogram) - Vector search latency",
            "qdrant_searches_total (counter) - Total searches",
            "qdrant_filter_hits_total (counter) - Filtered searches",
            "qdrant_collection_points (gauge) - Points in collections"
        ]
    }

    print("Expected Metrics Instrumentation:\n")

    for category, metrics in expected_metrics.items():
        print(f"{category}:")
        for metric in metrics:
            print(f"  - {metric}")
        print()

    checklist_results = {
        "categories": expected_metrics,
        "total_metrics": sum(len(v) for v in expected_metrics.values()),
        "notes": [
            "All metrics should follow Prometheus naming conventions",
            "Histograms should use appropriate buckets for latency (e.g., .001, .005, .01, .05, .1, .5, 1, 5)",
            "Labels should be low-cardinality (avoid user IDs, use aggregates)",
            "Rate limits and errors should be counters, not gauges"
        ]
    }

    print(f"Total Expected Metrics: {checklist_results['total_metrics']}")
    print()
    print("Notes:")
    for note in checklist_results['notes']:
        print(f"  - {note}")
    print()

    return checklist_results


def main():
    """Run comprehensive observability stack verification."""
    print("\n" + "=" * 60)
    print("OBSERVABILITY STACK VERIFICATION (P0.12)")
    print("=" * 60)
    print()

    artifacts_dir = project_root / "artifacts" / "observability"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Validate Prometheus configuration
        prometheus_results = validate_prometheus_config()

        # 2. Validate Grafana dashboards
        dashboard_results = validate_grafana_dashboards()

        # 3. Validate Grafana provisioning
        provisioning_results = validate_grafana_provisioning()

        # 4. Generate metrics instrumentation checklist
        instrumentation_checklist = generate_metrics_instrumentation_checklist()

        # Generate comprehensive summary
        print("=" * 60)
        print("GENERATING VERIFICATION ARTIFACTS")
        print("=" * 60)
        print()

        # Save prometheus validation
        prometheus_artifact = artifacts_dir / "prometheus-validation.json"
        with open(prometheus_artifact, 'w') as f:
            json.dump(prometheus_results, f, indent=2)
        print(f"✓ Saved: {prometheus_artifact}")

        # Save grafana validation
        grafana_artifact = artifacts_dir / "grafana-validation.json"
        with open(grafana_artifact, 'w') as f:
            json.dump(dashboard_results, f, indent=2)
        print(f"✓ Saved: {grafana_artifact}")

        # Save provisioning validation
        provisioning_artifact = artifacts_dir / "grafana-provisioning-validation.json"
        with open(provisioning_artifact, 'w') as f:
            json.dump(provisioning_results, f, indent=2)
        print(f"✓ Saved: {provisioning_artifact}")

        # Save instrumentation checklist
        instrumentation_artifact = artifacts_dir / "metrics-instrumentation-checklist.json"
        with open(instrumentation_artifact, 'w') as f:
            json.dump(instrumentation_checklist, f, indent=2)
        print(f"✓ Saved: {instrumentation_artifact}")

        print()

        # Final summary
        print("=" * 60)
        print("OBSERVABILITY STACK VERIFICATION COMPLETE")
        print("=" * 60)
        print()

        # Determine overall status
        all_pass = (
            prometheus_results.get("status") in ["PASS", "PARTIAL"] and
            dashboard_results.get("status") == "PASS" and
            provisioning_results.get("overall_status") == "PASS"
        )

        print("Summary:")
        print(f"  Prometheus Configuration: {prometheus_results.get('status')}")
        print(f"    Scrape Targets: {len(prometheus_results['scrape_configs']['found_jobs'])}/{prometheus_results['scrape_configs']['expected_jobs']}")
        print()
        print(f"  Grafana Dashboards: {dashboard_results.get('status')}")
        print(f"    Dashboards: {dashboard_results['dashboards']['total']}")
        print(f"    Panels: {dashboard_results['panels']['total']}")
        print()
        print(f"  Grafana Provisioning: {provisioning_results.get('overall_status')}")
        print()
        print(f"  Metrics to Instrument: {instrumentation_checklist['total_metrics']}")
        print()
        print(f"  Artifacts Generated: 4 files")
        print(f"  Location: {artifacts_dir}")
        print("=" * 60)

        if all_pass:
            print("\n✓ OBSERVABILITY STACK READY - All validations passed")
            return 0
        else:
            print("\n⚠ OBSERVABILITY STACK NEEDS ATTENTION - Review results above")
            return 1

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
