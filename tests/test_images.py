import pytest

from books_scrapy.items import BooksDetailScrapyItem
from books_scrapy.pipelines import LibrosImagesPipeline


class FakeSettings:
    def __init__(self, valores):
        self.valores = valores

    def getint(self, clave, default=0):
        return int(self.valores.get(clave, default))


class FakeSpider:
    def __init__(self, settings):
        self.settings = settings


class FakeInfo:
    def __init__(self, spider):
        self.spider = spider


def item(upc="abc123", url="http://x/img.jpg"):
    return BooksDetailScrapyItem(
        title="t",
        price=1.0,
        availability=True,
        rating=1,
        book_link="http://x",
        upc=upc,
        category="c",
        img_url=url,
    )


@pytest.fixture(autouse=True)
def contador_en_cero():
    # solicitadas es atributo de CLASE: sobrevive entre instancias y tests
    LibrosImagesPipeline.solicitadas = 0
    yield
    LibrosImagesPipeline.solicitadas = 0


def pipeline(tmp_path):
    from scrapy.utils.test import get_crawler

    crawler = get_crawler(settings_dict={"IMAGES_STORE": str(tmp_path)})
    return LibrosImagesPipeline.from_crawler(crawler)


def test_file_path_nombre_por_upc(tmp_path):
    p = pipeline(tmp_path)
    assert p.file_path(None, item=item()) == "abc123.jpg"


def test_item_completed_guarda_ruta_del_exito(tmp_path):
    p = pipeline(tmp_path)
    resultado = p.item_completed([(True, {"path": "abc123.jpg"})], item(), None)
    assert resultado.img_path == "abc123.jpg"


def test_item_completed_sin_exitos_queda_none(tmp_path):
    p = pipeline(tmp_path)
    resultado = p.item_completed([(False, {})], item(), None)
    assert resultado.img_path is None


def test_get_media_requests_un_request_por_img_url(tmp_path):
    p = pipeline(tmp_path)
    info = FakeInfo(FakeSpider(FakeSettings({})))
    requests = list(p.get_media_requests(item(), info))
    assert len(requests) == 1
    assert requests[0].url == "http://x/img.jpg"


def test_get_media_requests_sin_img_url_no_pide_nada(tmp_path):
    p = pipeline(tmp_path)
    info = FakeInfo(FakeSpider(FakeSettings({})))
    assert list(p.get_media_requests(item(url=None), info)) == []


def test_images_limit_corta_las_descargas(tmp_path):
    p = pipeline(tmp_path)
    info = FakeInfo(FakeSpider(FakeSettings({"IMAGES_LIMIT": 2})))
    pedidas = sum(
        len(list(p.get_media_requests(item(upc=f"u{n}"), info))) for n in range(4)
    )
    assert pedidas == 2
