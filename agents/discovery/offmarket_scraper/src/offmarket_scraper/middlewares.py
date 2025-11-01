"""Scrapy middlewares for handling JavaScript rendering and validation"""
import logging
from typing import Optional, Union
from scrapy import signals, Spider
from scrapy.http import HtmlResponse, Request
from scrapy.exceptions import IgnoreRequest
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
import asyncio

logger = logging.getLogger(__name__)


class PlaywrightMiddleware:
    """
    Middleware to render JavaScript-heavy pages using Playwright

    Usage:
        Add 'use_playwright': True to request.meta to enable Playwright rendering

    Example:
        yield scrapy.Request(
            url='https://example.com',
            callback=self.parse,
            meta={'use_playwright': True}
        )
    """

    def __init__(self, crawler):
        self.crawler = crawler
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.playwright = None

        # Get settings
        self.browser_type = crawler.settings.get('PLAYWRIGHT_BROWSER_TYPE', 'chromium')
        self.launch_options = crawler.settings.get('PLAYWRIGHT_LAUNCH_OPTIONS', {})

    @classmethod
    def from_crawler(cls, crawler):
        """Factory method to create middleware from crawler"""
        middleware = cls(crawler)
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware

    async def _init_browser(self):
        """Initialize Playwright browser"""
        if self.browser is None:
            self.playwright = await async_playwright().start()

            if self.browser_type == 'chromium':
                self.browser = await self.playwright.chromium.launch(**self.launch_options)
            elif self.browser_type == 'firefox':
                self.browser = await self.playwright.firefox.launch(**self.launch_options)
            elif self.browser_type == 'webkit':
                self.browser = await self.playwright.webkit.launch(**self.launch_options)
            else:
                raise ValueError(f"Unknown browser type: {self.browser_type}")

            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=self.crawler.settings.get('USER_AGENT'),
            )

            logger.info(f"Playwright browser initialized: {self.browser_type}")

    def spider_opened(self, spider: Spider):
        """Called when spider is opened"""
        logger.info(f"Opening spider: {spider.name}")

    def spider_closed(self, spider: Spider):
        """Called when spider is closed - cleanup Playwright"""
        if self.browser:
            asyncio.get_event_loop().run_until_complete(self._close_browser())
        logger.info(f"Closing spider: {spider.name}")

    async def _close_browser(self):
        """Close Playwright browser"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Playwright browser closed")

    def process_request(self, request: Request, spider: Spider):
        """
        Process request - render with Playwright if use_playwright is True

        Returns HtmlResponse if Playwright is used, None otherwise (passes to downloader)
        """
        if request.meta.get('use_playwright', False):
            # Run async rendering in sync context
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self._render_page(request, spider))

        return None  # Let Scrapy's default downloader handle it

    async def _render_page(self, request: Request, spider: Spider) -> Union[HtmlResponse, IgnoreRequest]:
        """
        Render page with Playwright and return HtmlResponse
        """
        await self._init_browser()

        page: Optional[Page] = None
        try:
            page = await self.context.new_page()

            # Get custom timeout or use default
            timeout = request.meta.get('playwright_timeout', 30000)

            # Navigate to page
            logger.debug(f"Playwright rendering: {request.url}")
            response = await page.goto(request.url, timeout=timeout, wait_until='networkidle')

            # Wait for specific selector if provided
            wait_selector = request.meta.get('playwright_wait_selector')
            if wait_selector:
                await page.wait_for_selector(wait_selector, timeout=timeout)

            # Execute custom JavaScript if provided
            custom_js = request.meta.get('playwright_js')
            if custom_js:
                await page.evaluate(custom_js)

            # Additional wait time if specified
            additional_wait = request.meta.get('playwright_wait_ms', 0)
            if additional_wait > 0:
                await asyncio.sleep(additional_wait / 1000)

            # Get page content
            content = await page.content()

            # Create Scrapy response
            return HtmlResponse(
                url=request.url,
                body=content,
                encoding='utf-8',
                request=request,
                status=response.status if response else 200
            )

        except PlaywrightTimeoutError as e:
            logger.error(f"Playwright timeout for {request.url}: {e}")
            raise IgnoreRequest(f"Playwright timeout: {e}")

        except Exception as e:
            logger.error(f"Playwright error for {request.url}: {e}")
            raise IgnoreRequest(f"Playwright error: {e}")

        finally:
            if page:
                await page.close()

    def process_exception(self, request: Request, exception: Exception, spider: Spider):
        """Process exceptions from Playwright"""
        logger.error(f"Exception processing request {request.url}: {exception}")
        return None


class ValidationMiddleware:
    """
    Middleware to validate spider output

    Ensures items yielded by spiders conform to expected format
    """

    def process_spider_output(self, response, result, spider: Spider):
        """Process and validate items yielded by spider"""
        for item in result:
            # Pass through non-item results (like requests)
            if not hasattr(item, '__getitem__'):
                yield item
                continue

            # Validate required fields
            required_fields = ['source', 'source_id', 'url']
            missing_fields = [field for field in required_fields if field not in item]

            if missing_fields:
                logger.warning(
                    f"Dropping item from {response.url}: missing required fields {missing_fields}"
                )
                continue

            yield item

    def process_spider_exception(self, response, exception: Exception, spider: Spider):
        """Handle exceptions from spiders"""
        logger.error(f"Spider exception for {response.url}: {exception}")
