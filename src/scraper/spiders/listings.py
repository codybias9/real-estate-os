import scrapy
from scrapy.http import Response
from typing import Any
from scraper.items import BookItem
class ListingsSpider(scrapy.Spider):
    name = "listings"
    allowed_domains = ["books.toscrape.com"]
    start_urls = ["https://books.toscrape.com/"]
    def parse(self, response: Response, **kwargs: Any):
        self.logger.info(f"Scraping page: {response.url}")
        for book in response.css("article.product_pod"):
            item = BookItem()
            item["title"] = book.css("h3 a::attr(title)").get()
            item["price"] = book.css("p.price_color::text").get()
            yield item
        next_page = response.css("li.next a::attr(href)").get()
        if next_page is not None:
            self.logger.info(f"Found next page: {next_page}")
            yield response.follow(next_page, callback=self.parse)
