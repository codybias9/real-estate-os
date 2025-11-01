"""Main entry point for off-market scraper

Provides CLI interface to run Scrapy spiders.
"""
import sys
import logging
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# Import all spiders
from offmarket_scraper.spiders.fsbo_spider import FsboSpider, FsboDetailSpider

logger = logging.getLogger(__name__)


def run_spider(spider_name: str, **kwargs):
    """
    Run a specific spider with arguments

    Args:
        spider_name: Name of spider to run (e.g., 'fsbo')
        **kwargs: Spider arguments
    """
    # Get Scrapy settings
    settings = get_project_settings()

    # Create crawler process
    process = CrawlerProcess(settings)

    # Map spider names to classes
    spiders = {
        'fsbo': FsboSpider,
        'fsbo_detail': FsboDetailSpider,
    }

    spider_class = spiders.get(spider_name)
    if not spider_class:
        logger.error(f"Unknown spider: {spider_name}")
        logger.info(f"Available spiders: {', '.join(spiders.keys())}")
        sys.exit(1)

    # Start crawling
    process.crawl(spider_class, **kwargs)
    process.start()


def main():
    """
    CLI entry point

    Usage:
        python -m offmarket_scraper.scraper fsbo --state=NV --city=Las-Vegas
        python -m offmarket_scraper.scraper fsbo --county=clark_nv
    """
    if len(sys.argv) < 2:
        print("Usage: python -m offmarket_scraper.scraper <spider_name> [args]")
        print("\nAvailable spiders:")
        print("  fsbo           - FSBO.com listing scraper")
        print("  fsbo_detail    - FSBO.com detail page scraper")
        print("\nExamples:")
        print("  python -m offmarket_scraper.scraper fsbo --state=NV --city=Las-Vegas")
        print("  python -m offmarket_scraper.scraper fsbo --county=clark_nv")
        print("  python -m offmarket_scraper.scraper fsbo_detail --urls='url1,url2'")
        sys.exit(1)

    spider_name = sys.argv[1]

    # Parse command-line arguments
    kwargs = {}
    for arg in sys.argv[2:]:
        if arg.startswith('--'):
            key_value = arg[2:].split('=', 1)
            if len(key_value) == 2:
                key, value = key_value
                kwargs[key] = value

    # Run spider
    logger.info(f"Starting spider: {spider_name}")
    logger.info(f"Arguments: {kwargs}")

    run_spider(spider_name, **kwargs)


if __name__ == "__main__":
    main()
