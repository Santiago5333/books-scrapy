import scrapy

from books_scrapy.items import BooksDetailScrapyItem


class BooksCatalogSpider(scrapy.Spider):
    name = "books"
    # allowed_domains = ["http://books.toscrape.com"]
    start_urls = ["http://books.toscrape.com/catalogue/page-1.html"]

    def __init__(self, pagina=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pagina = pagina
        if pagina:
            self.start_urls = [
                f"https://books.toscrape.com/catalogue/page-{pagina}.html"
            ]

    def parse(self, response):
        for libro in response.css("article.product_pod"):
            basicos = {
                "title": libro.css("h3 a::attr(title)").get(),
                "price": libro.css("p.price_color::text").get(),
                "rating": libro.css("p.star-rating::attr(class)").get().split()[-1],
                "book_link": response.urljoin(libro.css("h3 a::attr(href)").get()),
            }
            yield response.follow(
                basicos["book_link"], self.parse_detail, cb_kwargs={"basicos": basicos}
            )

        siguiente = response.css("li.next a::attr(href)").get()
        if siguiente and not self.pagina:
            yield response.follow(siguiente, self.parse)

    def parse_detail(self, response, basicos):
        yield BooksDetailScrapyItem(
            **basicos,
            upc=response.css("table tr:nth-child(1) td::text").get(),
            category=response.css("ul.breadcrumb li:nth-child(3) a::text").get(),
            img_url=response.urljoin(
                response.css("div.item.active img::attr(src)").get()
            ),
            description=response.css("#product_description + p::text").get(),
            availability=response.css("div.product_main p.instock.availability::text").getall()[-1].strip(),
        )
