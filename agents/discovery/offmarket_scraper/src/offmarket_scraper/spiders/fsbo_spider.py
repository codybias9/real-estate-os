"""FSBO.com spider for scraping For-Sale-By-Owner listings

This spider demonstrates how to scrape listings from FSBO.com using Playwright
for JavaScript rendering.
"""
import logging
from typing import Iterator
from urllib.parse import urljoin
from scrapy.http import Response
from ..items import PropertyItem
from .base import BasePropertySpider

logger = logging.getLogger(__name__)


class FsboSpider(BasePropertySpider):
    """
    Spider for scraping FSBO.com listings

    Usage:
        scrapy crawl fsbo -a state=NV -a city=Las-Vegas

    Or with county config:
        scrapy crawl fsbo -a county=clark_nv
    """

    name = 'fsbo'
    source_name = 'fsbo.com'
    allowed_domains = ['fsbo.com']

    # Spider arguments
    state: str = 'NV'
    city: str = 'Las-Vegas'
    max_pages: int = 10

    def __init__(self, state: str = None, city: str = None, max_pages: int = None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if state:
            self.state = state
        if city:
            self.city = city
        if max_pages:
            self.max_pages = int(max_pages)

        # Try to get from config
        if self.config:
            scrape_params = self.config.get('scrape_params', {})
            self.state = scrape_params.get('state', self.state)
            self.city = scrape_params.get('city', self.city)
            self.max_pages = scrape_params.get('max_pages', self.max_pages)

    def get_start_urls(self) -> list[str]:
        """Generate start URLs for FSBO search"""
        # FSBO URL format: https://www.fsbo.com/nevada/las-vegas
        base_url = f"https://www.fsbo.com/{self.state.lower()}/{self.city.lower()}"

        urls = [base_url]

        # Add pagination URLs
        for page in range(2, self.max_pages + 1):
            urls.append(f"{base_url}?page={page}")

        logger.info(f"Starting FSBO scrape for {self.city}, {self.state} ({len(urls)} pages)")
        return urls

    def parse(self, response: Response) -> Iterator:
        """
        Parse FSBO listing page

        Note: FSBO.com uses JavaScript, so requests should use:
            meta={'use_playwright': True}
        """
        self.stats['pages_scraped'] += 1

        # Extract listing cards (adjust selectors based on actual HTML)
        listing_cards = response.css('.property-card, .listing-item')

        logger.info(f"Found {len(listing_cards)} listings on {response.url}")

        for card in listing_cards:
            try:
                item = self.extract_listing(card, response)
                if item:
                    self.stats['listings_found'] += 1
                    yield item

                    # Yield provenance tuples for this item
                    provenance_tuples = self.get_provenance_tuples()
                    for prov_tuple in provenance_tuples:
                        self.stats['provenance_tuples'] += 1
                        yield prov_tuple

            except Exception as e:
                logger.error(f"Error extracting listing: {e}")
                self.stats['errors'] += 1

    def extract_listing(self, selector, response: Response) -> PropertyItem:
        """
        Extract data from a single listing card

        Args:
            selector: Scrapy selector for listing card
            response: Full page response

        Returns:
            PropertyItem with extracted data
        """
        # Extract listing URL (required)
        listing_url = selector.css('a.property-link::attr(href)').get()
        if not listing_url:
            listing_url = selector.css('a::attr(href)').get()

        if not listing_url:
            logger.warning("No URL found for listing")
            return None

        listing_url = urljoin(response.url, listing_url)

        # Extract source ID from URL or data attribute
        source_id = selector.css('::attr(data-listing-id)').get()
        if not source_id:
            # Try to extract from URL
            import re
            match = re.search(r'/listing/(\d+)', listing_url)
            source_id = match.group(1) if match else listing_url.split('/')[-1]

        # Begin provenance tracking for this entity
        entity_key = f"{self.source_name}:{source_id}"
        self.begin_entity_tracking(entity_key, listing_url)

        # Extract basic information (with provenance tracking)
        address = self.extract_text(selector, css='.property-address::text, .address::text')
        if address:
            self.track_field('address', address)

        city = self.extract_text(selector, css='.property-city::text, .city::text')
        if city:
            self.track_field('city', city)
        elif self.city:
            city = self.city
            self.track_field('city', city, confidence=0.5, method='computed')

        state = self.extract_text(selector, css='.property-state::text, .state::text')
        if state:
            self.track_field('state', state)
        elif self.state:
            state = self.state
            self.track_field('state', state, confidence=0.5, method='computed')

        zip_code = self.extract_text(selector, css='.property-zip::text, .zip::text')
        if zip_code:
            self.track_field('zip_code', zip_code)

        # Extract price
        price_text = self.extract_text(selector, css='.property-price::text, .price::text')
        listing_price = None
        if price_text:
            # Remove $ and commas, convert to float
            price_clean = price_text.replace('$', '').replace(',', '').strip()
            try:
                listing_price = float(price_clean)
                self.track_field('listing_price', listing_price, confidence=0.9)
            except (ValueError, TypeError):
                pass

        # Extract property details
        bedrooms = self.extract_number(selector, css='.beds::text, .bedrooms::text')
        if bedrooms:
            self.track_field('bedrooms', bedrooms)

        bathrooms = self.extract_number(selector, css='.baths::text, .bathrooms::text')
        if bathrooms:
            self.track_field('bathrooms', bathrooms)

        square_footage = self.extract_number(selector, css='.sqft::text, .square-feet::text')
        if square_footage:
            self.track_field('square_footage', square_footage)

        # Extract images
        image_urls = self.extract_list(selector, css='img::attr(src)')
        if image_urls:
            self.track_field('image_urls', image_urls)

        primary_image = image_urls[0] if image_urls else None
        if primary_image:
            self.track_field('primary_image_url', primary_image)

        # Extract description
        description = self.extract_text(selector, css='.property-description::text, .description::text')
        if description:
            self.track_field('description', description, confidence=0.8)

        # Track metadata fields
        self.track_field('property_type', 'Single Family', confidence=0.7, method='computed')
        self.track_field('listing_status', 'Active', confidence=0.9, method='computed')

        # Create item
        item = self.create_item(
            source_id=source_id,
            url=listing_url,
            address=address,
            city=city or self.city,
            state=state or self.state,
            zip_code=zip_code,
            listing_price=listing_price,
            bedrooms=int(bedrooms) if bedrooms else None,
            bathrooms=bathrooms,
            square_footage=int(square_footage) if square_footage else None,
            property_type='Single Family',  # FSBO is typically residential
            description=description,
            image_urls=image_urls,
            primary_image_url=primary_image,
            listing_status='Active',
        )

        return item


class FsboDetailSpider(BasePropertySpider):
    """
    Spider for scraping detailed FSBO listing pages

    This spider takes a list of listing URLs and scrapes full details.

    Usage:
        scrapy crawl fsbo_detail -a urls="url1,url2,url3"
    """

    name = 'fsbo_detail'
    source_name = 'fsbo.com'
    allowed_domains = ['fsbo.com']

    def __init__(self, urls: str = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls_list = urls.split(',') if urls else []

    def get_start_urls(self) -> list[str]:
        """Return list of URLs to scrape"""
        return self.start_urls_list

    def parse(self, response: Response) -> Iterator:
        """
        Parse detailed listing page

        Note: Should use Playwright for JavaScript rendering:
            meta={'use_playwright': True}
        """
        self.stats['pages_scraped'] += 1

        try:
            item = self.extract_detail_page(response)
            if item:
                self.stats['listings_found'] += 1
                yield item

                # Yield provenance tuples for this item
                provenance_tuples = self.get_provenance_tuples()
                for prov_tuple in provenance_tuples:
                    self.stats['provenance_tuples'] += 1
                    yield prov_tuple

        except Exception as e:
            logger.error(f"Error extracting detail page: {e}")
            self.stats['errors'] += 1

    def extract_detail_page(self, response: Response) -> PropertyItem:
        """
        Extract detailed data from listing detail page

        Args:
            response: Scrapy Response for detail page

        Returns:
            PropertyItem with full listing data
        """
        # Extract source ID from URL
        import re
        match = re.search(r'/listing/(\d+)', response.url)
        source_id = match.group(1) if match else response.url.split('/')[-1]

        # Begin provenance tracking for this entity
        entity_key = f"{self.source_name}:{source_id}"
        self.begin_entity_tracking(entity_key, response.url)

        # Extract comprehensive details (with provenance tracking)
        address = self.extract_text(response, css='h1.property-address::text, .full-address::text')
        if address:
            self.track_field('address', address, confidence=0.95)

        city = self.extract_text(response, css='.property-city::text')
        if city:
            self.track_field('city', city, confidence=0.95)

        state = self.extract_text(response, css='.property-state::text')
        if state:
            self.track_field('state', state, confidence=0.95)

        zip_code = self.extract_text(response, css='.property-zip::text')
        if zip_code:
            self.track_field('zip_code', zip_code, confidence=0.95)

        listing_price = self.extract_number(response, css='.listing-price::text, .price::text')
        if listing_price:
            self.track_field('listing_price', listing_price, confidence=0.95)

        property_type = self.extract_text(response, css='.property-type::text')
        if property_type:
            self.track_field('property_type', property_type, confidence=0.9)

        bedrooms = self.extract_number(response, css='.bedrooms .value::text')
        if bedrooms:
            self.track_field('bedrooms', bedrooms, confidence=0.95)

        bathrooms = self.extract_number(response, css='.bathrooms .value::text')
        if bathrooms:
            self.track_field('bathrooms', bathrooms, confidence=0.95)

        square_footage = self.extract_number(response, css='.square-feet .value::text')
        if square_footage:
            self.track_field('square_footage', square_footage, confidence=0.9)

        lot_size_sqft = self.extract_number(response, css='.lot-size .value::text')
        if lot_size_sqft:
            self.track_field('lot_size_sqft', lot_size_sqft, confidence=0.9)

        year_built = self.extract_number(response, css='.year-built .value::text')
        if year_built:
            self.track_field('year_built', year_built, confidence=0.9)

        description = self.extract_text(response, css='.property-description::text')
        if description:
            self.track_field('description', description, confidence=0.85)

        features = self.extract_list(response, css='.features li::text')
        if features:
            self.track_field('features', features, confidence=0.9)

        parking_spaces = self.extract_number(response, css='.parking .value::text')
        if parking_spaces:
            self.track_field('parking_spaces', parking_spaces, confidence=0.9)

        garage_spaces = self.extract_number(response, css='.garage .value::text')
        if garage_spaces:
            self.track_field('garage_spaces', garage_spaces, confidence=0.9)

        image_urls = self.extract_list(response, css='.property-images img::attr(src)')
        if image_urls:
            self.track_field('image_urls', image_urls, confidence=0.95)

        owner_name = self.extract_text(response, css='.seller-name::text, .owner-name::text')
        if owner_name:
            self.track_field('owner_name', owner_name, confidence=0.85)

        agent_phone = self.extract_text(response, css='.contact-phone::text, .phone::text')
        if agent_phone:
            self.track_field('agent_phone', agent_phone, confidence=0.9)

        agent_email = self.extract_text(response, css='.contact-email::text, .email::text')
        if agent_email:
            self.track_field('agent_email', agent_email, confidence=0.9)

        days_on_market = self.extract_number(response, css='.days-on-market .value::text')
        if days_on_market:
            self.track_field('days_on_market', days_on_market, confidence=0.9)

        # Track computed fields
        self.track_field('listing_status', 'Active', confidence=0.9, method='computed')

        # Create item
        item = self.create_item(
            source_id=source_id,
            url=response.url,

            # Address
            address=address,
            city=city,
            state=state,
            zip_code=zip_code,

            # Price
            listing_price=listing_price,

            # Property details
            property_type=property_type,
            bedrooms=int(bedrooms) if bedrooms else None,
            bathrooms=bathrooms,
            square_footage=int(square_footage) if square_footage else None,
            lot_size_sqft=int(lot_size_sqft) if lot_size_sqft else None,
            year_built=int(year_built) if year_built else None,

            # Additional details
            description=description,
            features=features,
            parking_spaces=int(parking_spaces) if parking_spaces else None,
            garage_spaces=int(garage_spaces) if garage_spaces else None,

            # Images
            image_urls=image_urls,

            # Contact info
            owner_name=owner_name,
            agent_phone=agent_phone,
            agent_email=agent_email,

            # Status
            listing_status='Active',
            days_on_market=int(days_on_market) if days_on_market else None,
        )

        return item
