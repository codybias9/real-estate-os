"""
SQLAlchemy models for Real Estate OS data processing platform
"""
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, JSON, Float, Boolean, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import enum

Base = declarative_base()


class ProspectStatus(str, enum.Enum):
    """Status for prospect queue items"""
    NEW = "new"
    PROCESSING = "processing"
    ENRICHED = "enriched"
    SCORED = "scored"
    FAILED = "failed"


class JobStatus(str, enum.Enum):
    """Status for pipeline jobs"""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProspectQueue(Base):
    """
    Prospect queue table - initial ingestion point for scraped data
    """
    __tablename__ = "prospect_queue"

    id = Column(Integer, primary_key=True)
    source = Column(String(255), nullable=False, index=True)
    source_id = Column(String(255), unique=True, nullable=False)
    url = Column(Text, nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String(50), default=ProspectStatus.NEW, nullable=False, index=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class Property(Base):
    """
    Enriched property data
    """
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True)
    prospect_id = Column(Integer, index=True)  # Reference to prospect_queue
    address = Column(Text, nullable=False)
    city = Column(String(255), index=True)
    state = Column(String(50), index=True)
    zip_code = Column(String(20), index=True)

    # Property details
    property_type = Column(String(100))
    bedrooms = Column(Integer)
    bathrooms = Column(Float)
    sqft = Column(Integer)
    lot_size = Column(Float)
    year_built = Column(Integer)

    # Pricing
    price = Column(Float)
    estimated_value = Column(Float)

    # Enrichment data
    enrichment_data = Column(JSON)  # Additional enriched data
    enrichment_sources = Column(JSON)  # Track which sources provided data

    # Metadata
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class ScrapingJob(Base):
    """
    Track scraping job executions
    """
    __tablename__ = "scraping_jobs"

    id = Column(Integer, primary_key=True)
    dag_id = Column(String(255), nullable=False, index=True)
    dag_run_id = Column(String(255), index=True)
    source = Column(String(255), nullable=False, index=True)

    # Job details
    status = Column(SQLEnum(JobStatus), default=JobStatus.QUEUED, nullable=False, index=True)
    items_scraped = Column(Integer, default=0)
    items_failed = Column(Integer, default=0)

    # Timing
    started_at = Column(TIMESTAMP(timezone=True))
    completed_at = Column(TIMESTAMP(timezone=True))

    # Metadata
    config = Column(JSON)  # Scraping configuration
    error_log = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class EnrichmentJob(Base):
    """
    Track enrichment pipeline executions
    """
    __tablename__ = "enrichment_jobs"

    id = Column(Integer, primary_key=True)
    dag_id = Column(String(255), nullable=False, index=True)
    dag_run_id = Column(String(255), index=True)
    property_id = Column(Integer, index=True)

    # Job details
    status = Column(SQLEnum(JobStatus), default=JobStatus.QUEUED, nullable=False, index=True)
    enrichment_type = Column(String(100), index=True)  # e.g., "property_data", "market_data"

    # Timing
    started_at = Column(TIMESTAMP(timezone=True))
    completed_at = Column(TIMESTAMP(timezone=True))

    # Results
    data_sources_used = Column(JSON)  # Which APIs/sources were used
    fields_enriched = Column(JSON)  # Which fields were enriched
    error_log = Column(Text)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class PropertyScore(Base):
    """
    ML-based property scoring results
    """
    __tablename__ = "property_scores"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, nullable=False, index=True)
    dag_run_id = Column(String(255), index=True)

    # Scores
    overall_score = Column(Float, index=True)
    investment_score = Column(Float)
    risk_score = Column(Float)
    roi_estimate = Column(Float)

    # Score breakdown
    score_components = Column(JSON)  # Detailed score breakdown

    # Model info
    model_version = Column(String(100))
    features_used = Column(JSON)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class PipelineRun(Base):
    """
    Track overall pipeline execution metrics
    """
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True)
    dag_id = Column(String(255), nullable=False, index=True)
    dag_run_id = Column(String(255), nullable=False, index=True)
    execution_date = Column(TIMESTAMP(timezone=True), nullable=False)

    # Status
    status = Column(String(50), index=True)  # queued, running, success, failed

    # Timing
    started_at = Column(TIMESTAMP(timezone=True))
    completed_at = Column(TIMESTAMP(timezone=True))
    duration_seconds = Column(Integer)

    # Metrics
    tasks_total = Column(Integer)
    tasks_success = Column(Integer)
    tasks_failed = Column(Integer)

    # Data
    config = Column(JSON)
    logs = Column(Text)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class DataQualityMetric(Base):
    """
    Track data quality metrics over time
    """
    __tablename__ = "data_quality_metrics"

    id = Column(Integer, primary_key=True)
    metric_type = Column(String(100), nullable=False, index=True)
    metric_name = Column(String(255), nullable=False, index=True)

    # Metric values
    value = Column(Float, nullable=False)
    threshold = Column(Float)
    is_passing = Column(Boolean)

    # Context
    entity_type = Column(String(100))  # property, prospect, pipeline
    entity_id = Column(Integer)

    # Metadata
    details = Column(JSON)
    measured_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
