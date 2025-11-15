"""Property listings spider - generates simulated property data for demo."""

import scrapy
from scrapy.http import Response
from typing import Any
from scraper.items import PropertyItem
from scraper.property_generator import PropertyDataGenerator


class ListingsSpider(scrapy.Spider):
    """Spider that generates simulated property listings for demo purposes."""

    name = "listings"
    allowed_domains = []  # No external domains since we're generating data

    # Custom settings for this spider
    custom_settings = {
        'CONCURRENT_REQUESTS': 1,
        'DOWNLOAD_DELAY': 0,
    }

    def __init__(self, count=50, *args, **kwargs):
        """Initialize spider with number of properties to generate."""
        super(ListingsSpider, self).__init__(*args, **kwargs)
        self.count = int(count)
        self.logger.info(f"Initialized ListingsSpider to generate {self.count} properties")

    def start_requests(self):
        """Start the spider by generating a dummy request."""
        # We don't actually fetch anything, just use this to trigger parse
        yield scrapy.Request(
            url='data:,',  # Empty data URL
            callback=self.parse,
            dont_filter=True
        )

    def parse(self, response: Response, **kwargs: Any):
        """Generate simulated property data."""
        self.logger.info(f"Generating {self.count} simulated property listings...")

        # Generate properties
        properties = PropertyDataGenerator.generate_batch(count=self.count, source="simulated_mls")

        for prop_data in properties:
            item = PropertyItem()

            # Populate item with generated data
            item['source'] = prop_data['source']
            item['source_id'] = prop_data['source_id']
            item['url'] = prop_data['url']
            item['address'] = prop_data['address']
            item['city'] = prop_data['city']
            item['state'] = prop_data['state']
            item['zip_code'] = prop_data['zip_code']
            item['county'] = prop_data['county']
            item['latitude'] = prop_data['latitude']
            item['longitude'] = prop_data['longitude']
            item['property_type'] = prop_data['property_type']
            item['price'] = prop_data['price']
            item['bedrooms'] = prop_data['bedrooms']
            item['bathrooms'] = prop_data['bathrooms']
            item['sqft'] = prop_data['sqft']
            item['lot_size'] = prop_data['lot_size']
            item['year_built'] = prop_data['year_built']
            item['listing_date'] = prop_data['listing_date']
            item['description'] = prop_data['description']
            item['features'] = prop_data['features']
            item['images'] = prop_data['images']
            item['status'] = prop_data['status']
            item['metadata'] = prop_data['metadata']

            self.logger.info(f"Generated property: {prop_data['address']}, {prop_data['city']}, {prop_data['state']} - ${prop_data['price']:,}")

            yield item

        self.logger.info(f"Successfully generated {self.count} property listings")
