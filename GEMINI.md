# Real Estate Automation Platform — Build Context

## Overview
This system ingests off-market property listings, enriches them with public data, scores them using a trained LightGBM model, and generates investment packets for outreach. It runs fully containerized via Kubernetes + Airflow.

## Key Components
- DAGs trigger via Airflow's KubernetesPodOperator
- Agents are Dockerized (Playwright/Scrapy/HTTP)
- Helm charts configure Postgres, RabbitMQ, MinIO, Qdrant
- Data flows from discovery → enrichment → scoring → docgen → email

## Directory Structure
- scripts/: auditing build progress
- dags/: Airflow DAGs per phase
- gents/: all microservices (scrapers, enrichers, scorers, etc.)
- charts/helm/: infra config
- 	emplates/: MJML templates for emails
- k8s/: Kubernetes deploy files
- config/counties/: YAML configs per target geography

## Active Phases
- ✅ Phase 0–2: Core infra + off-market scraper agent
- 🟡 Phase 3–5: Enrichment, scoring, and docgen pending
- ⏳ Phase 6–8: Email, UI, multi-tenant later

## Credentials/Secrets
- $Env:DB_DSN: Postgres DSN
- MINIO_ALIAS: for model/doc uploads
- SendGrid API: not created yet

## Goals Now
- Scaffold DAGs + agents for enrichment and scoring
- Add tests and templates
- Use Gemini to scaffold/draft/refactor as needed
