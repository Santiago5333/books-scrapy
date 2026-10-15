# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface

import re
import sqlite3
from pathlib import Path

import scrapy
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem
from scrapy.pipelines.images import ImagesPipeline

RATINGS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

COLUMNAS = (
    "upc",
    "title",
    "price",
    "availability",
    "stock",
    "rating",
    "category",
    "description",
    "book_link",
    "img_url",
)


def parse_price(texto):
    if not texto:
        return None
    limpio = re.sub(r"[^\d.,]", "", texto)
    if not limpio:
        return None

    if "," in limpio and "." in limpio:
        if limpio.rfind(",") > limpio.rfind("."):
            limpio = limpio.replace(".", "").replace(",", ".")
        else:
            limpio = limpio.replace(",", "")
    elif "," in limpio:
        if re.search(r",\d{2}$", limpio):
            limpio = limpio.replace(",", ".")

        else:
            limpio = limpio.replace(",", "")
    try:
        return float(limpio)
    except ValueError:
        return None


class DuplicadoPipeline:
    def open_spider(self):
        self.vistos = set()

    def process_item(self, item):
        upc = ItemAdapter(item).get("upc")
        if upc in self.vistos:
            raise DropItem(f"Duplicado: {upc}")
        self.vistos.add(upc)
        return item


class BooksScrapyPipeline:
    def process_item(self, item):
        adapter = ItemAdapter(item)
        rating = adapter.get("rating")
        adapter["rating"] = RATINGS.get(rating) if rating else None

        price = parse_price(adapter.get("price"))
        if price is None:
            raise DropItem(f"Precio Invalido en {adapter.get('book_link')}")
        adapter["price"] = price

        disp = adapter.get("availability") or ""
        m = re.search(r"\((\d+) available\)", disp)
        adapter["stock"] = int(m.group(1)) if m else None
        adapter["availability"] = "in stock" in disp.lower()

        desc = adapter.get("description")
        if desc:
            desc = re.sub(r"\s*\.\.\.more\s*$", "", desc).strip()
        adapter["description"] = desc or None

        return item


class SQLPipeline:
    def __init__(self, ruta):

        self.ruta = Path(ruta)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings.get("SQLITE_PATH", "libros.db"))

    def open_spider(self):
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.ruta)
        self.cur = self.conn.cursor()
        self.contador = 0
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS libros (
        upc TEXT PRIMARY KEY,
        title TEXT,
        price REAL,
        availability INTEGER,
        stock INTEGER,
        rating INTEGER,
        category TEXT,
        description TEXT,
        book_link TEXT,
        img_url TEXT
        )
        """)
        self.conn.commit()

    def process_item(self, item):
        a = ItemAdapter(item)
        datos = {c: a.get(c) for c in COLUMNAS}
        datos["availability"] = int(bool(datos["availability"]))

        cols = ", ".join(COLUMNAS)
        params = ", ".join(f":{c}" for c in COLUMNAS)
        self.cur.execute(
            f"INSERT OR REPLACE INTO libros({cols}) VALUES({params})",
            datos,
        )
        self.contador += 1
        if self.contador % 100 == 0:
            self.conn.commit()
        return item

    def close_spider(self):
        self.conn.commit()
        self.conn.close()


class LibrosImagesPipeline(ImagesPipeline):
    solicitadas = 0

    def get_media_requests(self, item, info):
        limite = info.spider.settings.getint("IMAGES_LIMIT", 0)
        if limite and self.solicitadas >= limite:
            return

        url = ItemAdapter(item).get("img_url")
        if url:
            self.solicitadas += 1
            yield scrapy.Request(url)

    def file_path(self, request, response=None, info=None, *, item=None):
        return f"{ItemAdapter(item).get('upc')}.jpg"

    def item_completed(self, results, item, info):
        rutas = [r["path"] for ok, r in results if ok]
        ItemAdapter(item)["img_path"] = rutas[0] if rutas else None
        return item
