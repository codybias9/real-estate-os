"""Scrapy items for property data."""

import scrapy


class PropertyItem(scrapy.Item):
    """Property listing item."""

    # Source information
    source = scrapy.Field()
    source_id = scrapy.Field()
    url = scrapy.Field()

    # Location
    address = scrapy.Field()
    city = scrapy.Field()
    state = scrapy.Field()
    zip_code = scrapy.Field()
    county = scrapy.Field()
    latitude = scrapy.Field()
    longitude = scrapy.Field()

    # Property details
    property_type = scrapy.Field()
    price = scrapy.Field()
    bedrooms = scrapy.Field()
    bathrooms = scrapy.Field()
    sqft = scrapy.Field()
    lot_size = scrapy.Field()
    year_built = scrapy.Field()

    # Listing information
    listing_date = scrapy.Field()
    description = scrapy.Field()
    features = scrapy.Field()
    images = scrapy.Field()

    # Status
    status = scrapy.Field()

    # Metadata
    metadata = scrapy.Field()


# Keep BookItem for backwards compatibility with existing DAGs
class BookItem(scrapy.Item):
    title = scrapy.Field()
    price = scrapy.Field()
