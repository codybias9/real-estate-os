"""Scrapy settings for offmarket_scraper project

For more information on Scrapy settings see:
https://docs.scrapy.org/en/latest/topics/settings.html
"""
import os

BOT_NAME = 'offmarket_scraper'

SPIDER_MODULES = ['offmarket_scraper.spiders']
NEWSPIDER_MODULE = 'offmarket_scraper.spiders'

# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False  # Real estate sites often block bots, adjust per site

# Configure maximum concurrent requests
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 4

# Configure a delay for requests to the same domain (seconds)
DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True

# Disable cookies unless needed for authentication
COOKIES_ENABLED = False

# Disable Telnet Console
TELNETCONSOLE_ENABLED = False

# Override the default request headers
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# Enable or disable spider middlewares
SPIDER_MIDDLEWARES = {
    'offmarket_scraper.middlewares.ValidationMiddleware': 543,
}

# Enable or disable downloader middlewares
DOWNLOADER_MIDDLEWARES = {
    'offmarket_scraper.middlewares.PlaywrightMiddleware': 585,
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': 90,
}

# Enable or disable extensions
EXTENSIONS = {
    'scrapy.extensions.telnet.TelnetConsole': None,
}

# Configure item pipelines
ITEM_PIPELINES = {
    'offmarket_scraper.pipelines.ValidationPipeline': 100,
    'offmarket_scraper.pipelines.DuplicatesPipeline': 200,
    'offmarket_scraper.pipelines.DatabasePipeline': 300,
}

# Enable and configure the AutoThrottle extension
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
HTTPCACHE_ENABLED = False
HTTPCACHE_EXPIRATION_SECS = 0
HTTPCACHE_DIR = 'httpcache'
HTTPCACHE_IGNORE_HTTP_CODES = []
HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'

# Retry settings
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429]

# Timeout settings
DOWNLOAD_TIMEOUT = 30

# Database settings (from environment)
DATABASE_URL = os.getenv('DB_DSN', 'postgresql://postgres:postgres@localhost:5432/realestate')

# Playwright settings
PLAYWRIGHT_BROWSER_TYPE = 'chromium'  # chromium, firefox, or webkit
PLAYWRIGHT_LAUNCH_OPTIONS = {
    'headless': os.getenv('PLAYWRIGHT_HEADLESS', 'true').lower() == 'true',
    'args': [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--disable-gpu',
        '--window-size=1920x1080',
    ]
}

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
LOG_DATEFORMAT = '%Y-%m-%d %H:%M:%S'

# Stats
STATS_CLASS = 'scrapy.statscollectors.MemoryStatsCollector'

# Request fingerprinter
REQUEST_FINGERPRINTER_IMPLEMENTATION = '2.7'
