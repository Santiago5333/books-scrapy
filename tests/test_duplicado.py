import pytest
from scrapy.exceptions import DropItem

from books_scrapy.items import BooksDetailScrapyItem
from books_scrapy.pipelines import DuplicadoPipeline


def item(upc):
    return BooksDetailScrapyItem(
        title="t",
        price=1.0,
        availability=True,
        rating=1,
        book_link="http://x",
        upc=upc,
        category="c",
        img_url="http://i",
    )


def pipeline():
    p = DuplicadoPipeline()
    p.open_spider()
    return p


def test_primer_item_pasa():
    assert pipeline().process_item(item("a")) is not None


def test_mismo_upc_segunda_vez_tira_dropitem():
    p = pipeline()
    p.process_item(item("a"))
    with pytest.raises(DropItem, match="Duplicado: a"):
        p.process_item(item("a"))


def test_upc_distinto_pasa():
    p = pipeline()
    p.process_item(item("a"))
    assert p.process_item(item("b")) is not None


def test_open_spider_reinicia_vistos():
    p = pipeline()
    p.process_item(item("a"))
    p.open_spider()
    assert p.process_item(item("a")) is not None
