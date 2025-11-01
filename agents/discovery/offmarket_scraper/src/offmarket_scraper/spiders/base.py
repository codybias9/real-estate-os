"""Base spider class for real estate listing scrapers

Provides common functionality for all listing spiders.
"""
import logging
from typing import Iterator, Optional, Dict, Any
from abc import ABC, abstractmethod
import yaml
from pathlib import Path
from scrapy import Spider as ScrapySpider
from scrapy.http import Response, Request
from ..items import PropertyItem

logger = logging.getLogger(__name__)


class BasePropertySpider(ScrapySpider, ABC):
    """
    Abstract base class for property listing spiders

    Subclasses must implement:
        - parse() method to extract listings
        - get_start_urls() to return initial URLs

    Provides:
        - Configuration loading
        - Common data extraction helpers
        - Error handling
        - Rate limiting support
    """

    # Must be set by subclass
    name: str = None
    source_name: str = None  # Identifier for database (e.g., 'zillow', 'fsbo')

    def __init__(self, county: Optional[str] = None, config_path: Optional[str] = None, *args, **kwargs):
        """
        Initialize spider with county configuration

        Args:
            county: County identifier (e.g., 'clark_nv')
            config_path: Path to county configuration file
        """
        super().__init__(*args, **kwargs)

        self.county = county
        self.config = {}

        # Load configuration if provided
        if config_path:
            self.load_config(config_path)
        elif county:
            self.load_config_for_county(county)

        # Statistics
        self.stats = {
            'pages_scraped': 0,
            'listings_found': 0,
            'errors': 0
        }

    def load_config(self, config_path: str):
        """Load configuration from YAML file"""
        try:
            path = Path(config_path)
            if not path.exists():
                logger.warning(f"Config file not found: {config_path}")
                return

            with open(path, 'r') as f:
                self.config = yaml.safe_load(f)

            logger.info(f"Loaded configuration from {config_path}")

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")

    def load_config_for_county(self, county: str):
        """Load county-specific configuration"""
        # Look for config file in standard location
        config_dir = Path(__file__).parents[5] / 'config' / 'counties'
        config_file = config_dir / f"{county}.yaml"

        if config_file.exists():
            self.load_config(str(config_file))
        else:
            logger.warning(f"No configuration found for county: {county}")

    def start_requests(self) -> Iterator[Request]:
        """Generate initial requests from start URLs"""
        start_urls = self.get_start_urls()

        for url in start_urls:
            yield Request(
                url=url,
                callback=self.parse,
                errback=self.handle_error,
                dont_filter=True
            )

    @abstractmethod
    def get_start_urls(self) -> list[str]:
        """
        Return list of start URLs to scrape

        Must be implemented by subclass
        """
        pass

    @abstractmethod
    def parse(self, response: Response) -> Iterator[PropertyItem]:
        """
        Parse response and extract property listings

        Must be implemented by subclass

        Args:
            response: Scrapy Response object

        Yields:
            PropertyItem objects
        """
        pass

    def handle_error(self, failure):
        """Handle request errors"""
        self.stats['errors'] += 1
        logger.error(f"Request failed: {failure.request.url}")
        logger.error(f"Error: {failure.value}")

    def create_item(self, **kwargs) -> PropertyItem:
        """
        Helper to create PropertyItem with default values

        Args:
            **kwargs: Field values for the item

        Returns:
            PropertyItem
        """
        item = PropertyItem()

        # Set source automatically
        if 'source' not in kwargs:
            kwargs['source'] = self.source_name or self.name

        # Set all provided fields
        for key, value in kwargs.items():
            if key in item.fields:
                item[key] = value

        return item

    def extract_text(self, selector, css: str = None, xpath: str = None, default: str = None) -> Optional[str]:
        """
        Extract and clean text from selector

        Args:
            selector: Scrapy selector
            css: CSS selector (optional)
            xpath: XPath selector (optional)
            default: Default value if not found

        Returns:
            Extracted text or default
        """
        try:
            if css:
                result = selector.css(css).get()
            elif xpath:
                result = selector.xpath(xpath).get()
            else:
                result = selector.get()

            if result:
                # Clean whitespace
                return ' '.join(result.split()).strip()

            return default

        except Exception as e:
            logger.debug(f"Extract error: {e}")
            return default

    def extract_number(self, selector, css: str = None, xpath: str = None, default: Optional[float] = None) -> Optional[float]:
        """
        Extract number from text

        Args:
            selector: Scrapy selector
            css: CSS selector (optional)
            xpath: XPath selector (optional)
            default: Default value if not found

        Returns:
            Extracted number or default
        """
        text = self.extract_text(selector, css=css, xpath=xpath)

        if not text:
            return default

        try:
            # Remove non-numeric characters except . and -
            cleaned = ''.join(c for c in text if c.isdigit() or c in '.-')
            return float(cleaned) if cleaned else default
        except (ValueError, TypeError):
            return default

    def extract_list(self, selector, css: str = None, xpath: str = None) -> list[str]:
        """
        Extract list of text values

        Args:
            selector: Scrapy selector
            css: CSS selector (optional)
            xpath: XPath selector (optional)

        Returns:
            List of extracted strings
        """
        try:
            if css:
                results = selector.css(css).getall()
            elif xpath:
                results = selector.xpath(xpath).getall()
            else:
                return []

            # Clean each result
            return [' '.join(r.split()).strip() for r in results if r.strip()]

        except Exception as e:
            logger.debug(f"Extract list error: {e}")
            return []

    def closed(self, reason: str):
        """Called when spider is closed - log statistics"""
        logger.info("=" * 50)
        logger.info(f"Spider {self.name} closed: {reason}")
        logger.info(f"Pages scraped: {self.stats['pages_scraped']}")
        logger.info(f"Listings found: {self.stats['listings_found']}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info("=" * 50)
