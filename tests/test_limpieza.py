import pytest
from scrapy.exceptions import DropItem

from books_scrapy.items import BooksDetailScrapyItem
from books_scrapy.pipelines import BooksScrapyPipeline


def detalle(**overrides):
    """Item de detalle tal como sale del spider (valores crudos, pre-pipeline)."""
    datos = dict(
        title="Un libro",
        price="£51.77",
        availability="In stock (22 available)",
        rating="Five",
        book_link="http://books.toscrape.com/libro/index.html",
        upc="upc-1",
        category="Fiction",
        img_url="http://x/img.jpg",
        description="Buen libro ...more",
    )
    datos.update(overrides)
    return BooksDetailScrapyItem(**datos)


def test_campos_transformados_en_una_pasada():
    item = BooksScrapyPipeline().process_item(detalle())
    assert item.price == 51.77
    assert item.rating == 5
    assert item.stock == 22
    assert item.availability is True
    assert item.description == "Buen libro"


def test_rating_mapea_palabras_a_enteros():
    p = BooksScrapyPipeline()
    assert p.process_item(detalle(rating="One")).rating == 1
    assert p.process_item(detalle(rating="Three")).rating == 3


def test_rating_desconocido_o_ausente_queda_none():
    p = BooksScrapyPipeline()
    assert p.process_item(detalle(rating="Six")).rating is None
    assert p.process_item(detalle(rating=None)).rating is None


def test_precio_invalido_tira_dropitem():
    item = detalle(price="Gratis")
    with pytest.raises(DropItem, match="Precio Invalido"):
        BooksScrapyPipeline().process_item(item)


def test_stock_sin_numero_en_availability():
    item = BooksScrapyPipeline().process_item(detalle(availability="In stock"))
    assert item.stock is None
    assert item.availability is True


def test_availability_ausente_es_false():
    item = BooksScrapyPipeline().process_item(detalle(availability=None))
    assert item.availability is False
    assert item.stock is None


def test_description_recorta_sufijo_more():
    item = BooksScrapyPipeline().process_item(
        detalle(description="Texto completo del libro. ...more")
    )
    assert item.description == "Texto completo del libro."


def test_description_vacia_o_none_queda_none():
    p = BooksScrapyPipeline()
    assert p.process_item(detalle(description=None)).description is None
    assert p.process_item(detalle(description="")).description is None
