import sqlite3

from books_scrapy.items import BooksDetailScrapyItem
from books_scrapy.pipelines import SQLPipeline


def item(n):
    """Item post-Limpieza (los tipos ya estan convertidos), como llega al SQL 400."""
    return BooksDetailScrapyItem(
        title=f"Libro {n}",
        price=10.5 + n,
        availability=True,
        rating=3,
        book_link=f"http://x/{n}",
        upc=f"upc-{n}",
        category="Fiction",
        img_url="http://i.jpg",
        description="desc",
        stock=n,
        img_path=f"upc-{n}.jpg",
    )


def pipeline(tmp_path):
    p = SQLPipeline(tmp_path / "sub" / "libros.db")
    p.open_spider()
    return p


def filas(ruta):
    conn = sqlite3.connect(ruta)
    filas = conn.execute("SELECT * FROM libros ORDER BY upc").fetchall()
    conn.close()
    return filas


def test_inserta_y_persiste_en_nueva_conexion(tmp_path):
    p = pipeline(tmp_path)
    p.process_item(item(1))
    p.close_spider()
    # orden de COLUMNAS: upc, title, price, availability, stock, rating,
    #                     category, description, book_link, img_url
    assert filas(tmp_path / "sub" / "libros.db") == [
        ("upc-1", "Libro 1", 11.5, 1, 1, 3, "Fiction", "desc", "http://x/1", "http://i.jpg")
    ]


def test_crea_directorio_padre(tmp_path):
    ruta = tmp_path / "a" / "b" / "libros.db"
    assert not ruta.parent.exists()
    SQLPipeline(ruta).open_spider()
    assert ruta.parent.exists()


def test_mismo_upc_reemplaza_sin_duplicar(tmp_path):
    p = pipeline(tmp_path)
    p.process_item(item(1))
    p.process_item(item(1))
    p.close_spider()
    assert len(filas(tmp_path / "sub" / "libros.db")) == 1


def test_commit_cada_100_y_commit_final_en_close(tmp_path):
    p = pipeline(tmp_path)
    for n in range(150):
        p.process_item(item(n))
    # crawl viva: solo lo commiteado (multiplos de 100) es visible afuera
    ruta = tmp_path / "sub" / "libros.db"
    conn = sqlite3.connect(ruta)
    visibles = conn.execute("SELECT COUNT(*) FROM libros").fetchone()[0]
    conn.close()
    assert visibles == 100
    p.close_spider()
    assert len(filas(ruta)) == 150


def test_availability_bool_se_guarda_como_int(tmp_path):
    p = pipeline(tmp_path)
    it = item(1)
    it.availability = False
    p.process_item(it)
    p.close_spider()
    conn = sqlite3.connect(tmp_path / "sub" / "libros.db")
    valor = conn.execute("SELECT availability FROM libros").fetchone()[0]
    conn.close()
    assert valor == 0
