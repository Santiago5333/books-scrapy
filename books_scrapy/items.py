# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

from dataclasses import dataclass


@dataclass
class BooksScrapyItem:
    # define the fields for your item here like:
    # name: str | None = None

    title: str
    price: float
    availability: bool
    rating: int
    book_link: str


@dataclass
class BooksDetailScrapyItem(BooksScrapyItem):
    upc: str
    category: str
    img_url: str
    description: str | None = None
    stock: int | None = None

    img_path: str | None = None
