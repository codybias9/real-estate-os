import scrapy
from scrapy.http import Response
from typing import Any

class ListingsSpider(scrapy.Spider):
    """
    A spider to scrape book listings from books.toscrape.com,
    serving as a template for real estate listings.
    """
    name = "listings"
    allowed_domains = ["books.toscrape.com"]
    start_urls = ["https://books.toscrape.com/"]

    def parse(self, response: Response, **kwargs: Any):
        """
        This method is called for each response. It extracts listing
        information and follows links to the next page.
        """
        self.logger.info(f"Scraping page: {response.url}")

        # Iterate over each book article on the page
        for book in response.css("article.product_pod"):
            yield {
                "title": book.css("h3 a::attr(title)").get(),
                "price": book.css("p.price_color::text").get(),
            }

        # Find the 'next' button and follow it if it exists
        next_page = response.css("li.next a::attr(href)").get()
        if next_page is not None:
            self.logger.info(f"Found next page: {next_page}")
            yield response.follow(next_page, callback=self.parse)
