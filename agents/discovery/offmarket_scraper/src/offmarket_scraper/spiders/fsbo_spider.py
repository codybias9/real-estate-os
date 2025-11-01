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

    def parse(self, response: Response) -> Iterator[PropertyItem]:
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

        # Extract basic information
        address = self.extract_text(selector, css='.property-address::text, .address::text')
        city = self.extract_text(selector, css='.property-city::text, .city::text')
        state = self.extract_text(selector, css='.property-state::text, .state::text')
        zip_code = self.extract_text(selector, css='.property-zip::text, .zip::text')

        # Extract price
        price_text = self.extract_text(selector, css='.property-price::text, .price::text')
        listing_price = None
        if price_text:
            # Remove $ and commas, convert to float
            price_clean = price_text.replace('$', '').replace(',', '').strip()
            try:
                listing_price = float(price_clean)
            except (ValueError, TypeError):
                pass

        # Extract property details
        bedrooms = self.extract_number(selector, css='.beds::text, .bedrooms::text')
        bathrooms = self.extract_number(selector, css='.baths::text, .bathrooms::text')
        square_footage = self.extract_number(selector, css='.sqft::text, .square-feet::text')

        # Extract images
        image_urls = self.extract_list(selector, css='img::attr(src)')
        primary_image = image_urls[0] if image_urls else None

        # Extract description
        description = self.extract_text(selector, css='.property-description::text, .description::text')

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

    def parse(self, response: Response) -> Iterator[PropertyItem]:
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

        # Extract comprehensive details (adjust selectors based on actual HTML)
        item = self.create_item(
            source_id=source_id,
            url=response.url,

            # Address
            address=self.extract_text(response, css='h1.property-address::text, .full-address::text'),
            city=self.extract_text(response, css='.property-city::text'),
            state=self.extract_text(response, css='.property-state::text'),
            zip_code=self.extract_text(response, css='.property-zip::text'),

            # Price
            listing_price=self.extract_number(response, css='.listing-price::text, .price::text'),

            # Property details
            property_type=self.extract_text(response, css='.property-type::text'),
            bedrooms=int(self.extract_number(response, css='.bedrooms .value::text') or 0),
            bathrooms=self.extract_number(response, css='.bathrooms .value::text'),
            square_footage=int(self.extract_number(response, css='.square-feet .value::text') or 0),
            lot_size_sqft=int(self.extract_number(response, css='.lot-size .value::text') or 0),
            year_built=int(self.extract_number(response, css='.year-built .value::text') or 0),

            # Additional details
            description=self.extract_text(response, css='.property-description::text'),
            features=self.extract_list(response, css='.features li::text'),
            parking_spaces=int(self.extract_number(response, css='.parking .value::text') or 0),
            garage_spaces=int(self.extract_number(response, css='.garage .value::text') or 0),

            # Images
            image_urls=self.extract_list(response, css='.property-images img::attr(src)'),

            # Contact info
            owner_name=self.extract_text(response, css='.seller-name::text, .owner-name::text'),
            agent_phone=self.extract_text(response, css='.contact-phone::text, .phone::text'),
            agent_email=self.extract_text(response, css='.contact-email::text, .email::text'),

            # Status
            listing_status='Active',
            days_on_market=int(self.extract_number(response, css='.days-on-market .value::text') or 0),
        )

        return item
