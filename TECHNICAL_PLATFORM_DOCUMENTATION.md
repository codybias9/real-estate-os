# Real Estate OS - Technical Platform Documentation

## 🏗️ System Architecture

Real Estate OS is a **data processing and automation platform** built on modern data engineering infrastructure:

### Core Infrastructure Stack

- **Orchestration**: Apache Airflow 3.0.2 with CeleryExecutor
- **Message Broker**: Redis 7.2
- **Database**: PostgreSQL 13
- **API**: FastAPI with async support
- **Web Scraping**: Scrapy framework
- **Data Enrichment**: Custom agents with S3 integration
- **Containerization**: Docker Compose
- **Deployment**: Kubernetes-ready

## 📊 Data Pipeline Architecture

### Pipeline Stages

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Scraping  │───▶│  Enrichment │───▶│   Scoring   │───▶│ Final Output│
│             │    │             │    │    (ML)     │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
     ▼                   ▼                   ▼                   ▼
ProspectQueue      Properties         PropertyScores     Reports/PDFs
```

### Data Flow

1. **Scraping Stage**: Web scrapers collect property listings
   - Sources: Zillow, Redfin, Realtor.com, off-market sources
   - Output: Raw data in `prospect_queue` table
   - Tracking: `scraping_jobs` table

2. **Enrichment Stage**: Data enrichment and validation
   - APIs: Census data, market data, property details
   - Output: Enriched records in `properties` table
   - Tracking: `enrichment_jobs` table

3. **Scoring Stage**: ML-based property evaluation
   - Models: Investment score, risk score, ROI estimation
   - Output: Scores in `property_scores` table
   - Tracking: Model versions and features used

4. **Document Generation**: Automated report creation
   - Generates property packets (PDFs)
   - Uses enriched data and scores

## 🚀 API Endpoints

### Base URL: `http://localhost:8000`

### Health & System Status

#### `GET /api/health/`
Basic health check
```json
{"status": "healthy", "timestamp": "2025-11-12T10:00:00Z"}
```

#### `GET /api/health/comprehensive`
Full system health check (API, Database, Airflow, System Resources)
```json
{
  "status": "healthy",
  "components": {
    "api": {"status": "healthy"},
    "database": {"status": "healthy"},
    "airflow": {"status": "healthy"},
    "system": {"status": "healthy", "memory_percent": 45.2, "disk_percent": 60.1}
  }
}
```

### Pipeline Monitoring

#### `GET /api/pipelines/overview`
High-level pipeline statistics and DAG status

#### `GET /api/pipelines/dags`
List all available DAGs with recent run history

#### `GET /api/pipelines/dags/{dag_id}`
Get specific DAG details

#### `GET /api/pipelines/dags/{dag_id}/runs`
Get execution history for a DAG

#### `GET /api/pipelines/dags/{dag_id}/runs/{run_id}/tasks`
Get task instances for a specific run

#### `POST /api/pipelines/dags/{dag_id}/trigger`
Manually trigger a DAG run

### Scraping Jobs

#### `GET /api/scraping/jobs`
List all scraping jobs with filters
- Query params: `status`, `source`, `limit`, `offset`

#### `GET /api/scraping/jobs/{job_id}`
Get details for a specific scraping job

#### `GET /api/scraping/queue`
View prospect queue (scraped data waiting for processing)

#### `GET /api/scraping/stats/overview`
Scraping statistics and metrics
```json
{
  "jobs": {
    "total": 120,
    "running": 2,
    "successful": 95,
    "failed": 5,
    "success_rate": 79.17
  },
  "prospects": {
    "total": 1250,
    "new": 150,
    "processed": 1000,
    "processing_rate": 80.0
  }
}
```

### Data Enrichment

#### `GET /api/enrichment/jobs`
List enrichment jobs with filters

#### `GET /api/enrichment/properties`
List enriched properties
- Query params: `city`, `state`, `property_type`, `limit`, `offset`

#### `GET /api/enrichment/properties/{property_id}`
Get full enriched property details including all data sources

#### `GET /api/enrichment/stats/overview`
Enrichment statistics

#### `GET /api/enrichment/stats/data-quality`
Data completeness metrics by field
```json
{
  "total_properties": 1000,
  "overall_completeness": 87.5,
  "field_completeness": {
    "address": {"count": 1000, "percentage": 100.0},
    "price": {"count": 950, "percentage": 95.0},
    "bedrooms": {"count": 920, "percentage": 92.0}
  }
}
```

### Property Scoring

#### `GET /api/scoring/scores`
List property scores with filters
- Query params: `min_score`, `max_score`, `limit`, `offset`

#### `GET /api/scoring/scores/{score_id}`
Get detailed score breakdown including all components

#### `GET /api/scoring/top-properties`
Get top-scored properties with full property details

#### `GET /api/scoring/stats/overview`
Scoring statistics and distribution
```json
{
  "total_scores": 500,
  "properties_scored": 450,
  "averages": {
    "overall_score": 72.5,
    "investment_score": 68.3,
    "risk_score": 45.2,
    "roi_estimate": 12.8
  },
  "score_distribution": {
    "0-20": 10,
    "20-40": 50,
    "40-60": 150,
    "60-80": 200,
    "80-100": 90
  }
}
```

#### `GET /api/scoring/stats/trends`
Scoring trends over time (daily averages)

### Platform Metrics

#### `GET /api/metrics/overview`
Comprehensive platform-wide metrics
```json
{
  "data_pipeline": {
    "total_prospects": 1250,
    "total_properties": 1000,
    "total_scores": 500,
    "new_prospects_pending": 150
  },
  "pipeline_execution": {
    "total_runs": 300,
    "successful_runs": 285,
    "success_rate": 95.0
  },
  "active_jobs": {
    "scraping": 2,
    "enrichment": 3,
    "total": 5
  },
  "recent_activity_24h": {
    "prospects_scraped": 85,
    "properties_enriched": 72,
    "properties_scored": 45
  }
}
```

#### `GET /api/metrics/throughput`
Daily throughput metrics (items processed per stage per day)

#### `GET /api/metrics/performance`
Average processing durations and error rates

#### `GET /api/metrics/funnel`
Data processing funnel (conversion rates between stages)

#### `GET /api/metrics/quality`
Data quality metrics and validation results

## 🗄️ Database Schema

### Core Tables

#### `prospect_queue`
Raw scraped data (initial ingestion point)
- `id`, `source`, `source_id`, `url`, `payload` (JSONB)
- `status`: new, processing, enriched, scored, failed
- Timestamps: `created_at`, `updated_at`

#### `properties`
Enriched property data
- Basic info: `address`, `city`, `state`, `zip_code`
- Property details: `property_type`, `bedrooms`, `bathrooms`, `sqft`, `lot_size`, `year_built`
- Pricing: `price`, `estimated_value`
- Enrichment: `enrichment_data` (JSONB), `enrichment_sources` (JSONB)
- Links to: `prospect_id`

#### `scraping_jobs`
Track scraping executions
- Job info: `dag_id`, `dag_run_id`, `source`
- Metrics: `items_scraped`, `items_failed`
- Status: queued, running, success, failed, cancelled
- Timing: `started_at`, `completed_at`

#### `enrichment_jobs`
Track enrichment executions
- Job info: `dag_id`, `dag_run_id`, `property_id`
- Type: `enrichment_type` (property_data, market_data, demographics)
- Results: `data_sources_used`, `fields_enriched`
- Status and timing

#### `property_scores`
ML-based property scores
- Scores: `overall_score`, `investment_score`, `risk_score`, `roi_estimate`
- Breakdown: `score_components` (JSONB)
- Model: `model_version`, `features_used` (JSONB)
- Links to: `property_id`, `dag_run_id`

#### `pipeline_runs`
Pipeline execution tracking
- Execution: `dag_id`, `dag_run_id`, `execution_date`
- Status: queued, running, success, failed
- Metrics: `tasks_total`, `tasks_success`, `tasks_failed`
- Duration: `duration_seconds`

#### `data_quality_metrics`
Data quality measurements
- Metric: `metric_type`, `metric_name`, `value`, `threshold`
- Status: `is_passing` (boolean)
- Context: `entity_type`, `entity_id`

## 🔧 Development Setup

### Prerequisites
- Docker and Docker Compose
- Python 3.9+
- PostgreSQL 13+

### Running the Platform

1. **Start Infrastructure Services**
   ```bash
   docker-compose up -d
   ```
   This starts: Airflow (scheduler, worker, apiserver), PostgreSQL, Redis

2. **Set up Database**
   ```bash
   # Run Alembic migrations
   cd db
   alembic upgrade head
   ```

3. **Seed Demo Data** (optional)
   ```bash
   python api/seed_demo_data.py
   ```

4. **Start API Server**
   ```bash
   cd api
   pip install -r requirements.txt
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Access Services**
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Airflow UI: http://localhost:8080 (user: airflow, pass: airflow)

### Environment Variables

Required environment variables:
```bash
# Database
DB_DSN=postgresql://airflow:airflow@postgres:5432/airflow

# Airflow
AIRFLOW_API_URL=http://airflow-apiserver:8080/api/v1
AIRFLOW_USERNAME=airflow
AIRFLOW_PASSWORD=airflow
```

## 📈 Available DAGs

### `scrape_listings`
Web scraping pipeline
- Scrapes property listings from configured sources
- Stores raw data in `prospect_queue`
- Creates `scraping_jobs` records

### `discovery_offmarket`
Off-market property discovery
- Placeholder for custom discovery logic
- Can integrate with multiple data sources

### `enrichment_property`
Data enrichment pipeline
- Enriches properties from `prospect_queue`
- Calls external APIs for additional data
- Creates enriched `properties` records
- Tracks in `enrichment_jobs`

### `score_master`
Property scoring pipeline
- Applies ML models to enriched properties
- Generates investment scores, risk scores, ROI estimates
- Creates `property_scores` records

### `docgen_packet`
Document generation pipeline
- Generates property packets (PDFs)
- Uses enriched data and scores

## 🎯 Key Features Demonstrated

### 1. **Pipeline Orchestration**
- Distributed task execution with Celery
- DAG-based workflow management
- Task dependency handling
- Retry logic and error handling

### 2. **Data Processing**
- Multi-stage data pipeline
- Data validation and quality checks
- Enrichment from multiple sources
- ML-based scoring

### 3. **Monitoring & Observability**
- Real-time pipeline status
- Job execution tracking
- Performance metrics
- Data quality metrics

### 4. **Scalability**
- Containerized services
- Kubernetes-ready deployments
- Distributed worker pools
- Message queue buffering

### 5. **API-First Design**
- RESTful API with OpenAPI docs
- Comprehensive endpoint coverage
- Async operations support
- CORS-enabled for frontend integration

## 🔍 Demo Data

The demo data script (`api/seed_demo_data.py`) creates:
- 50 prospect queue items (various statuses)
- 35 enriched properties
- 20 scraping jobs (with success/failure mix)
- 30 enrichment jobs
- 25 property scores
- 40 pipeline runs (across different DAGs)
- 50 data quality metrics

This demonstrates the full data flow and provides realistic data for API testing and frontend development.

## 📝 Next Steps

1. **Frontend Dashboard**: Build React dashboard consuming these APIs
2. **Real Scrapers**: Implement actual web scraping logic
3. **ML Models**: Add real property scoring models
4. **Authentication**: Add API authentication and authorization
5. **Monitoring**: Add Prometheus/Grafana for metrics
6. **Testing**: Add comprehensive test suite
7. **CI/CD**: Set up automated deployment pipelines

## 🚦 API Testing

### Using the Interactive Docs

Visit http://localhost:8000/docs to access the interactive API documentation where you can test all endpoints.

### Example Requests

```bash
# Get pipeline overview
curl http://localhost:8000/api/pipelines/overview

# List scraping jobs
curl http://localhost:8000/api/scraping/jobs?limit=10

# Get enrichment statistics
curl http://localhost:8000/api/enrichment/stats/overview

# Get top-scored properties
curl http://localhost:8000/api/scoring/top-properties?limit=20

# Get platform metrics
curl http://localhost:8000/api/metrics/overview

# Check system health
curl http://localhost:8000/api/health/comprehensive
```

## 📚 Additional Resources

- [Airflow Documentation](https://airflow.apache.org/docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Scrapy Documentation](https://docs.scrapy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
