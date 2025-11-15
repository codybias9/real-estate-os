"""SQLAlchemy database models for Real Estate OS."""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Boolean,
    TIMESTAMP,
    Date,
    ForeignKey,
    Index,
    JSON,
    ARRAY,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

Base = declarative_base()


class Ping(Base):
    """Health check table."""

    __tablename__ = "ping"
    id = Column(Integer, primary_key=True)
    ts = Column(TIMESTAMP(timezone=True), server_default=func.now())


class Property(Base):
    """Core property table."""

    __tablename__ = "properties"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Source information
    source = Column(String(255), nullable=False, index=True)
    source_id = Column(String(255), nullable=False, unique=True, index=True)
    url = Column(Text)

    # Location
    address = Column(String(500), nullable=False)
    city = Column(String(255), nullable=False, index=True)
    state = Column(String(2), nullable=False, index=True)
    zip_code = Column(String(10), nullable=False, index=True)
    county = Column(String(255), index=True)
    latitude = Column(Float)
    longitude = Column(Float)

    # Property details
    property_type = Column(String(50), nullable=False, index=True)
    price = Column(Integer, nullable=False, index=True)
    bedrooms = Column(Integer)
    bathrooms = Column(Float)
    sqft = Column(Integer)
    lot_size = Column(Integer)
    year_built = Column(Integer)

    # Listing information
    listing_date = Column(TIMESTAMP(timezone=True))
    description = Column(Text)
    features = Column(ARRAY(Text))
    images = Column(ARRAY(Text))

    # Status
    status = Column(String(50), nullable=False, default="new", index=True)

    # Metadata
    extra_data = Column(JSON, default={})

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    enrichment = relationship("PropertyEnrichment", back_populates="property", uselist=False)
    score = relationship("PropertyScore", back_populates="property", uselist=False)
    documents = relationship("GeneratedDocument", back_populates="property")
    outreach_logs = relationship("OutreachLog", back_populates="property")

    # Indexes
    __table_args__ = (
        Index("idx_property_location", "city", "state", "zip_code"),
        Index("idx_property_type_status", "property_type", "status"),
        Index("idx_property_price_range", "price"),
    )


class PropertyEnrichment(Base):
    """Property enrichment data table."""

    __tablename__ = "property_enrichment"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Assessor data
    apn = Column(String(255))
    tax_assessment_value = Column(Integer)
    tax_assessment_year = Column(Integer)
    annual_tax_amount = Column(Integer)

    # Ownership and sales history
    owner_name = Column(String(500))
    owner_type = Column(String(100))
    last_sale_date = Column(Date)
    last_sale_price = Column(Integer)

    # Property characteristics
    legal_description = Column(Text)
    zoning = Column(String(100))
    land_use = Column(String(255))

    # Building details
    building_sqft = Column(Integer)
    stories = Column(Integer)
    units = Column(Integer)
    parking_spaces = Column(Integer)

    # Neighborhood data
    school_district = Column(String(255))
    elementary_school = Column(String(255))
    middle_school = Column(String(255))
    high_school = Column(String(255))
    school_rating = Column(Float)

    # Location metrics
    walkability_score = Column(Integer)
    transit_score = Column(Integer)
    bike_score = Column(Integer)

    # Crime and safety
    crime_rate = Column(String(50))
    crime_index = Column(Integer)

    # Market data
    median_home_value = Column(Integer)
    appreciation_1yr = Column(Float)
    appreciation_5yr = Column(Float)
    median_rent = Column(Integer)

    # Nearby amenities
    nearby_parks = Column(ARRAY(Text))
    nearby_shopping = Column(ARRAY(Text))
    nearby_restaurants = Column(ARRAY(Text))
    distance_to_downtown = Column(Float)

    # Additional data
    flood_zone = Column(String(50))
    earthquake_zone = Column(String(50))
    hoa_fees = Column(Integer)

    # Metadata
    enrichment_source = Column(String(255))
    enrichment_metadata = Column(JSON, default={})

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    property = relationship("Property", back_populates="enrichment")


class PropertyScore(Base):
    """Property scoring table."""

    __tablename__ = "property_scores"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Overall score
    total_score = Column(Integer, nullable=False, index=True)

    # Score breakdown (stored as JSON for flexibility)
    score_breakdown = Column(JSON, nullable=False)

    # Features used (stored as JSON)
    features = Column(JSON, nullable=False)

    # Recommendation
    recommendation = Column(String(50), nullable=False, index=True)
    recommendation_reason = Column(Text, nullable=False)

    # Risk assessment
    risk_level = Column(String(50), nullable=False, index=True)
    risk_factors = Column(ARRAY(Text))

    # Model information
    model_version = Column(String(50), nullable=False)
    scoring_method = Column(String(50), nullable=False)

    # Confidence
    confidence_score = Column(Float, nullable=False)

    # Metadata
    scoring_metadata = Column(JSON, default={})

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    property = relationship("Property", back_populates="score")

    # Indexes
    __table_args__ = (
        Index("idx_score_recommendation", "total_score", "recommendation"),
        Index("idx_score_risk", "risk_level", "total_score"),
    )


class GeneratedDocument(Base):
    """Generated documents table."""

    __tablename__ = "generated_documents"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)

    # Document information
    document_type = Column(String(50), nullable=False, index=True)
    filename = Column(String(500), nullable=False)
    file_path = Column(Text)
    file_url = Column(Text)
    file_size = Column(Integer)
    mime_type = Column(String(100), default="application/pdf")

    # Generation status
    status = Column(String(50), nullable=False, default="pending", index=True)
    error_message = Column(Text)

    # Generation metadata
    template_version = Column(String(50))
    generated_by = Column(String(255))
    generation_time_ms = Column(Integer)

    # Additional metadata
    extra_data = Column(JSON, default={})

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    property = relationship("Property", back_populates="documents")

    # Indexes
    __table_args__ = (Index("idx_document_type_status", "document_type", "status"),)


class Campaign(Base):
    """Email campaign table."""

    __tablename__ = "campaigns"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Campaign details
    name = Column(String(500), nullable=False)
    description = Column(Text)

    # Email content
    subject = Column(String(500), nullable=False)
    email_template = Column(Text, nullable=False)

    # Targeting
    property_ids = Column(ARRAY(Integer), nullable=False)
    min_score = Column(Integer)
    max_score = Column(Integer)

    # Recipients
    recipient_emails = Column(ARRAY(Text), nullable=False)

    # Scheduling
    scheduled_send_time = Column(TIMESTAMP(timezone=True))

    # Status
    status = Column(String(50), nullable=False, default="draft", index=True)

    # Statistics
    total_recipients = Column(Integer, default=0)
    emails_sent = Column(Integer, default=0)
    emails_delivered = Column(Integer, default=0)
    emails_opened = Column(Integer, default=0)
    emails_clicked = Column(Integer, default=0)
    emails_replied = Column(Integer, default=0)
    emails_bounced = Column(Integer, default=0)
    emails_unsubscribed = Column(Integer, default=0)

    # Timing
    sent_at = Column(TIMESTAMP(timezone=True))
    completed_at = Column(TIMESTAMP(timezone=True))

    # Metadata
    extra_data = Column(JSON, default={})

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    outreach_logs = relationship("OutreachLog", back_populates="campaign")

    # Indexes
    __table_args__ = (Index("idx_campaign_status", "status", "scheduled_send_time"),)


class OutreachLog(Base):
    """Outreach email log table."""

    __tablename__ = "outreach_logs"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)

    # Email details
    recipient_email = Column(String(500), nullable=False, index=True)
    subject = Column(String(500), nullable=False)
    message_id = Column(String(500), index=True)

    # Status
    status = Column(String(50), nullable=False, default="pending", index=True)

    # Tracking
    sent_at = Column(TIMESTAMP(timezone=True))
    delivered_at = Column(TIMESTAMP(timezone=True))
    opened_at = Column(TIMESTAMP(timezone=True))
    clicked_at = Column(TIMESTAMP(timezone=True))
    replied_at = Column(TIMESTAMP(timezone=True))

    # Engagement metrics
    open_count = Column(Integer, default=0)
    click_count = Column(Integer, default=0)

    # Error handling
    error_message = Column(Text)
    bounce_reason = Column(Text)

    # Metadata
    extra_data = Column(JSON, default={})

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    campaign = relationship("Campaign", back_populates="outreach_logs")
    property = relationship("Property", back_populates="outreach_logs")

    # Indexes
    __table_args__ = (
        Index("idx_outreach_campaign_status", "campaign_id", "status"),
        Index("idx_outreach_recipient", "recipient_email", "status"),
    )
