"""Data models for scraped property listings

Uses Pydantic for validation and Scrapy Items for pipeline compatibility.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, validator, HttpUrl
from scrapy import Item, Field as ScrapyField


# ============================================================================
# Pydantic Models for Validation
# ============================================================================

class PropertyListing(BaseModel):
    """Validated property listing data model"""

    # Required fields
    source: str = Field(..., description="Data source identifier (e.g., 'zillow', 'redfin')")
    source_id: str = Field(..., description="Unique ID from source website")
    url: str = Field(..., description="Original listing URL")

    # Address fields
    address: Optional[str] = Field(None, description="Full street address")
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    county: Optional[str] = None

    # Property details
    property_type: Optional[str] = None  # Single Family, Condo, Townhouse, etc.
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    square_footage: Optional[int] = None
    lot_size_sqft: Optional[int] = None
    year_built: Optional[int] = None

    # Financial information
    listing_price: Optional[float] = Field(None, description="Asking price")
    price_per_sqft: Optional[float] = None
    estimated_value: Optional[float] = None
    tax_assessed_value: Optional[float] = None
    annual_tax_amount: Optional[float] = None
    hoa_fee: Optional[float] = None

    # Listing details
    listing_status: Optional[str] = None  # Active, Pending, Off Market, etc.
    days_on_market: Optional[int] = None
    listing_date: Optional[datetime] = None

    # Property features
    description: Optional[str] = None
    features: Optional[List[str]] = Field(default_factory=list)
    parking_spaces: Optional[int] = None
    garage_spaces: Optional[int] = None
    pool: Optional[bool] = None

    # Images
    image_urls: Optional[List[str]] = Field(default_factory=list)
    primary_image_url: Optional[str] = None

    # Contact information
    agent_name: Optional[str] = None
    agent_phone: Optional[str] = None
    agent_email: Optional[str] = None
    broker_name: Optional[str] = None

    # Owner information (if available)
    owner_name: Optional[str] = None
    owner_type: Optional[str] = None  # Individual, Trust, LLC, etc.

    # Metadata
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    raw_data: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @validator('listing_price', 'estimated_value', 'tax_assessed_value', pre=True)
    def parse_price(cls, v):
        """Parse price strings like '$450,000' to float"""
        if isinstance(v, str):
            # Remove currency symbols, commas, spaces
            v = v.replace('$', '').replace(',', '').replace(' ', '')
            try:
                return float(v)
            except ValueError:
                return None
        return v

    @validator('bedrooms', 'square_footage', 'lot_size_sqft', 'year_built', pre=True)
    def parse_int(cls, v):
        """Parse integer fields from strings"""
        if isinstance(v, str):
            # Remove non-numeric characters
            v = ''.join(filter(str.isdigit, v))
            try:
                return int(v) if v else None
            except ValueError:
                return None
        return v

    @validator('bathrooms', pre=True)
    def parse_bathrooms(cls, v):
        """Parse bathroom counts like '2.5' or '2 full, 1 half'"""
        if isinstance(v, str):
            # Try to extract first number
            import re
            match = re.search(r'(\d+(?:\.\d+)?)', v)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    return None
        return v

    @validator('zip_code', pre=True)
    def validate_zip(cls, v):
        """Validate ZIP code format"""
        if v and isinstance(v, str):
            import re
            # Extract 5 or 9 digit ZIP
            match = re.search(r'(\d{5}(?:-\d{4})?)', v)
            if match:
                return match.group(1)
        return v

    def to_prospect_queue_payload(self) -> Dict[str, Any]:
        """Convert to format expected by prospect_queue table"""
        return {
            "source": self.source,
            "source_id": self.source_id,
            "url": self.url,
            "payload": self.dict(exclude_none=False)
        }


# ============================================================================
# Scrapy Items (for pipeline compatibility)
# ============================================================================

class PropertyItem(Item):
    """Scrapy Item wrapper for PropertyListing"""

    # Required
    source = ScrapyField()
    source_id = ScrapyField()
    url = ScrapyField()

    # Address
    address = ScrapyField()
    city = ScrapyField()
    state = ScrapyField()
    zip_code = ScrapyField()
    county = ScrapyField()

    # Property details
    property_type = ScrapyField()
    bedrooms = ScrapyField()
    bathrooms = ScrapyField()
    square_footage = ScrapyField()
    lot_size_sqft = ScrapyField()
    year_built = ScrapyField()

    # Financial
    listing_price = ScrapyField()
    price_per_sqft = ScrapyField()
    estimated_value = ScrapyField()
    tax_assessed_value = ScrapyField()
    annual_tax_amount = ScrapyField()
    hoa_fee = ScrapyField()

    # Listing details
    listing_status = ScrapyField()
    days_on_market = ScrapyField()
    listing_date = ScrapyField()

    # Features
    description = ScrapyField()
    features = ScrapyField()
    parking_spaces = ScrapyField()
    garage_spaces = ScrapyField()
    pool = ScrapyField()

    # Images
    image_urls = ScrapyField()
    primary_image_url = ScrapyField()

    # Contact
    agent_name = ScrapyField()
    agent_phone = ScrapyField()
    agent_email = ScrapyField()
    broker_name = ScrapyField()

    # Owner
    owner_name = ScrapyField()
    owner_type = ScrapyField()

    # Metadata
    scraped_at = ScrapyField()
    raw_data = ScrapyField()
