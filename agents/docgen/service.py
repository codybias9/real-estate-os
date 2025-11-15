"""Document generation service for creating and managing investor memos."""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from db.models import Property, PropertyEnrichment, PropertyScore, GeneratedDocument
from .generator import InvestorMemoGenerator


class DocumentService:
    """Service for generating and managing property documents."""

    def __init__(self, db: Session):
        """
        Initialize the document service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.generator = InvestorMemoGenerator()

    def generate_investor_memo(self, property_id: int) -> GeneratedDocument:
        """
        Generate an investor memo PDF for a property.

        Args:
            property_id: ID of the property to generate memo for

        Returns:
            GeneratedDocument database record

        Raises:
            ValueError: If property, enrichment, or score data is missing
        """
        # Fetch property
        property_obj = self.db.query(Property).filter(Property.id == property_id).first()
        if not property_obj:
            raise ValueError(f"Property {property_id} not found")

        # Fetch enrichment data
        enrichment = self.db.query(PropertyEnrichment).filter(
            PropertyEnrichment.property_id == property_id
        ).first()
        if not enrichment:
            raise ValueError(f"Enrichment data not found for property {property_id}")

        # Fetch score data
        score = self.db.query(PropertyScore).filter(
            PropertyScore.property_id == property_id
        ).first()
        if not score:
            raise ValueError(f"Score data not found for property {property_id}")

        # Convert ORM objects to dictionaries
        property_data = self._property_to_dict(property_obj)
        enrichment_data = self._enrichment_to_dict(enrichment)
        score_data = self._score_to_dict(score)

        # Generate the PDF
        pdf_path = self.generator.generate_memo(property_data, enrichment_data, score_data)

        # Create database record
        document = GeneratedDocument(
            property_id=property_id,
            document_type='investor_memo',
            file_path=pdf_path,
            generated_at=datetime.utcnow(),
            metadata={
                'score': score.total_score,
                'recommendation': score.recommendation,
                'address': property_obj.address,
                'city': property_obj.city,
                'state': property_obj.state,
            }
        )

        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)

        # Update property status if needed
        if property_obj.status != 'documented':
            property_obj.status = 'documented'
            self.db.commit()

        return document

    def get_document(self, document_id: int) -> Optional[GeneratedDocument]:
        """Retrieve a generated document by ID."""
        return self.db.query(GeneratedDocument).filter(
            GeneratedDocument.id == document_id
        ).first()

    def get_property_documents(self, property_id: int) -> list[GeneratedDocument]:
        """Get all documents for a specific property."""
        return self.db.query(GeneratedDocument).filter(
            GeneratedDocument.property_id == property_id
        ).order_by(GeneratedDocument.generated_at.desc()).all()

    def _property_to_dict(self, prop: Property) -> dict:
        """Convert Property ORM object to dictionary."""
        return {
            'id': prop.id,
            'source': prop.source,
            'address': prop.address,
            'city': prop.city,
            'state': prop.state,
            'zip_code': prop.zip_code,
            'price': prop.price,
            'bedrooms': prop.bedrooms,
            'bathrooms': prop.bathrooms,
            'sqft': prop.sqft,
            'lot_size': prop.lot_size,
            'year_built': prop.year_built,
            'property_type': prop.property_type,
            'description': prop.description,
            'features': prop.features or [],
            'images': prop.images or [],
            'url': prop.url,
            'status': prop.status,
        }

    def _enrichment_to_dict(self, enrichment: PropertyEnrichment) -> dict:
        """Convert PropertyEnrichment ORM object to dictionary."""
        return {
            'property_id': enrichment.property_id,
            'tax_assessment_value': enrichment.tax_assessment_value,
            'annual_tax_amount': enrichment.annual_tax_amount,
            'last_sale_date': enrichment.last_sale_date,
            'last_sale_price': enrichment.last_sale_price,
            'owner_name': enrichment.owner_name,
            'owner_type': enrichment.owner_type,
            'ownership_length_years': enrichment.ownership_length_years,
            'zoning': enrichment.zoning,
            'school_district': enrichment.school_district,
            'school_rating': enrichment.school_rating,
            'walkability_score': enrichment.walkability_score,
            'crime_rate': enrichment.crime_rate,
            'median_income': enrichment.median_income,
            'population_growth': enrichment.population_growth,
            'unemployment_rate': enrichment.unemployment_rate,
            'median_home_price': enrichment.median_home_price,
            'median_rent': enrichment.median_rent,
            'vacancy_rate': enrichment.vacancy_rate,
            'days_on_market_avg': enrichment.days_on_market_avg,
        }

    def _score_to_dict(self, score: PropertyScore) -> dict:
        """Convert PropertyScore ORM object to dictionary."""
        return {
            'property_id': score.property_id,
            'total_score': score.total_score,
            'score_breakdown': score.score_breakdown or {},
            'features': score.features or {},
            'recommendation': score.recommendation,
            'recommendation_reason': score.recommendation_reason,
            'risk_level': score.risk_level,
            'risk_factors': score.risk_factors or [],
            'comparable_properties': score.comparable_properties or [],
        }


def generate_document_for_property(property_id: int, db: Session) -> GeneratedDocument:
    """
    Standalone function to generate a document for a property.
    Used by DAGs and background tasks.

    Args:
        property_id: ID of the property
        db: Database session

    Returns:
        Generated document record
    """
    service = DocumentService(db)
    return service.generate_investor_memo(property_id)
