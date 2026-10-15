# books-scrapy

Scraper de [books.toscrape.com](https://books.toscrape.com) escrito con Scrapy
2.19: un spider, una cadena de cuatro pipelines y tests sin red.

Es la segunda versión del mismo scraper. La primera —
[books-scraper](https://github.com/Santiago5333/books-scraper), con requests +
BeautifulSoup — resolvió todo a mano. Esta rehace el trabajo con el framework
para comparar las dos formas de construir lo mismo. El README termina con esa
comparativa.

## Corrida real (producto en disco, no exit code)

    scrapy crawl books

- 1000 libros (50 páginas completas), 1000 UPCs únicos, 0 items descartados.
- 37 minutos, 1818 requests, 0 errores. `finish_reason: finished`.
- Salidas: `data/libros.json` (1000 items ya limpios), `data/libros.db`
  (1000 rows), `data/images/` (1000 JPEG, ~21 MB).
- El repo incluye solo muestras en `data/muestras/` (3 libros + imágenes);
  el producto completo pesa demasiado para git.

## Estructura

    books-scrapy/
    ├── scrapy.cfg
    ├── requirements.txt
    ├── books_scrapy/
    │   ├── items.py            # dataclasses: BooksScrapyItem, BooksDetailScrapyItem
    │   ├── spiders/
    │   │   └── book_catalog.py # spider "books": catálogo → detalle → paginación
    │   ├── pipelines.py        # Limpieza, Duplicado, Imágenes, SQL
    │   └── settings.py         # delays, FEEDS, IMAGES_STORE, SQLITE_PATH, ITEM_PIPELINES
    ├── tests/                  # 30 tests (pytest), sin red
    ├── conftest.py
    └── data/                    # producto del crawl + muestras

## Setup

    uv venv .venv
    source .venv/bin/activate
    uv pip install -r requirements.txt

(o `python3 -m venv .venv` + `pip install -r requirements.txt`)

## Uso

    scrapy crawl books                                # sitio completo (1000 libros)
    scrapy crawl books -s CLOSESPIDER_ITEMCOUNT=20    # acotar por items
    scrapy crawl books -a pagina=3                     # arrancar en la página 3, sin paginar
    scrapy crawl books -s IMAGES_LIMIT=5               # limitar descargas de imágenes

Salidas automáticas (configuradas en `settings.py`):

- `FEEDS` → `data/libros.json` (utf-8, indent 2, overwrite).
- `SQLPipeline` → `data/libros.db`, tabla `libros` con `upc` como PK.
- `LibrosImagesPipeline` → `data/images/{upc}.jpg`.

## El spider

`parse` recorre los 20 `article.product_pod` de cada página, extrae los datos
básicos y delega en `parse_detail` vía `response.follow` con `cb_kwargs` (el
detalle completa el item). La paginación sigue `li.next a` hasta que se acaba.
La categoría sale del breadcrumb (`li:nth-child(3)`, tercero de cuatro: Home >
Books > *categoría* > *título*), la disponibilidad de
`div.product_main p.instock.availability` (ver lección 1) y el stock con la
regex `\((\d+) available\)` sobre el texto crudo antes de convertirlo a bool.

## Cadena de pipelines (settings.ITEM_PIPELINES)

    300  BooksScrapyPipeline (Limpieza)
         rating "Five"→5, "£51.77"→float (maneja coma decimal europea),
         "In stock (19 available)"→availability bool + stock int por regex,
         description sin " ...more". Precio inválido → DropItem.
    350  DuplicadoPipeline
         dedupe por UPC en memoria (set en open_spider). Repetido → DropItem.
    380  LibrosImagesPipeline (subclase de ImagesPipeline)
         descarga img_url, guarda {upc}.jpg (file_path), escribe item.img_path
         (item_completed con el primer resultado ok). Respeta IMAGES_LIMIT.
         No escribe en la DB: la fila no depende de que baje la imagen.
    400  SQLPipeline
         INSERT OR REPLACE por UPC (corrida repetida = seguro), commit cada
         100 items + commit final en close_spider.

El feed export recibe los items DESPUÉS de los pipelines, así que
`libros.json` sale ya limpio, sin versión cruda de ningún campo.

## Tests

    source .venv/bin/activate
    python -m pytest -q

30 tests, ninguno toca la red: parse_price (7: libra, coma europea, miles eu/us,
vacío, sin dígitos), limpieza (9: los tipos convertidos en una pasada, DropItem
por precio, description), duplicado (4), SQL (5: fila exacta, idempotencia,
commit-cada-100 visible desde una conexión nueva), imágenes (5: file_path por
UPC, item_completed, IMAGES_LIMIT). Instanciar ImagesPipeline en tests requiere
`get_crawler` de `scrapy.utils.test` + `from_crawler` (en 2.19 el `crawler` es
argumento obligatorio).

## Comparativa: requests + BeautifulSoup vs Scrapy

Mismo sitio, mismos datos, las dos versiones funcionando:

| Área | books-scraper (a mano) | books-scrapy (framework) |
|---|---|---|
| HTTP y reintentos | `requests.Session` + `HTTPAdapter` montado a mano | downloader del framework |
| Cortesía al sitio | `request_delay` del config | `DOWNLOAD_DELAY`, `ROBOTSTXT_OBEY`, `CONCURRENT_REQUESTS_PER_DOMAIN` |
| Concurrencia | secuencial; `ThreadPoolExecutor` solo para imágenes | scheduler del framework |
| Paginación | loop manual hasta `max_pages` | `response.follow(li.next)` hasta que no hay más |
| Parseo | `BeautifulSoup.select` | `response.css` + `.get()`/`.getall()` |
| Modelo de datos | dataclasses propias | dataclasses + `ItemAdapter` |
| Limpieza de datos | funciones del scraper | pipeline 300, con `DropItem` |
| Dedupe | set dentro de `scraper_all` | pipeline 350 dedicado |
| Imágenes | `download_image` + pool de hilos; bytes originales | `ImagesPipeline` subclase; re-encodadas (ver lección 9) |
| Almacenamiento | ABC `Storage` + JSON/CSV/SQLite + despachador `get_storage()` | pipelines + `FEEDS` + `SQLPipeline` |
| Configuración | `config.yaml` propio, selectores incluidos | `settings.py` del framework |
| CLI | `argparse` propio (`scrape`/`load`) | `scrapy crawl` + flags `-s`/`-a` |
| Tests | 32, fixtures de HTML descargados del sitio | 30, pipelines puros sin fixtures de HTML |
| Datos finales | 40 libros de muestra en el repo | 1000 libros verificados en disco |

La conclusión honesta: el framework no elimina las decisiones, las
reorganiza. Donde antes escribía el bucle de paginación, ahora escribo
`response.follow`; donde antes inventaba el despachador de storage, ahora
ordeno pipelines con prioridades. Las partes difíciles siguen siendo mías:
qué dato guardar, cómo normalizarlo, qué hace cada parte del pipeline y en
qué orden. Lo que cambia es la cantidad de infraestructura que dejo de
escribir (reintentos, concurrencia, throttling) y la cantidad de superficie
con convenciones establecidas que otro programador reconoce al leer el repo.

## Lecciones que dejó el framework

1. **El scope de un selector pesca más que el selector mismo.** La página de
   detalle tiene SIETE `p.instock.availability` (uno en `product_main`, seis
   en carruseles de recomendaciones). El selector sin scope caía en el
   carrusel: 19 de 20 libros quedaban con stock `None` y la suite en verde,
   porque los fixtures del proyecto hermano (un solo `p`) mintieron. Solo el
   smoke contra el sitio real lo encontró. Fix: `div.product_main
   p.instock.availability`.
2. **`CLOSESPIDER_PAGECOUNT` cuenta páginas (incluido el robots.txt), no
   items**: cerraba antes de llegar a los detalles y terminaba con 0 items.
   Para acotar por resultado, `CLOSESPIDER_ITEMCOUNT`.
3. **El commit cada N items pertenece al método por-item, nunca al hook de
   cierre.** En `close_spider` corre una sola vez → la transacción nunca se
   commiteaba en el camino → al morir se revertía entera: tabla creada con 0
   rows, silenciosa y con pinta de éxito. Ahora `process_item` commitea cada
   100 y `close_spider` solo el commit final. Hay un test que lo inmoviliza
   (conexión nueva a mitad de crawl: solo lo commiteado es visible).
4. **El feed export recibe items después de los pipelines.** El JSON de
   `FEEDS` sale limpio sin trabajo extra; no existe la salida cruda.
5. **Scrapy 2.19 deprecó el argumento `spider` en los hooks de pipeline.**
   Las firmas nuevas van sin `spider` y el manager las llama igual; quedarse
   en la firma vieja tira warnings por request.
6. **Items como dataclass + `item_completed` default = descarte silencioso.**
   El default mete los resultados en `item["images"]`; con dataclass, el campo
   no declarado revienta `KeyError`… que el default suprime: la imagen baja y
   el resultado se pierde sin ruido. Fix: pisar `item_completed` y escribir en
   un campo declarado (`img_path`).
7. **`get_media_requests` devuelve un iterable de Requests** (yield de a uno
   o lista); con strings explota con un TypeError poco obvio.
8. **`ITEM_PIPELINES` apuntando a una clase renombrada es código muerto
   ruidoso**: `ModuleNotFoundError` al arrancar el crawl. En config, los
   strings con nombre de clase se rompen al refactor: renombrar = actualizar
   settings.
9. **`ImagesPipeline` re-encodifica con Pillow** aunque el original ya sea
   JPEG: el sitio sirve progressive de ~52 KB y el pipeline guarda baseline de
   ~26 KB (mismas dimensiones). En el scraper a mano los bytes quedaban
   idénticos al original. Consecuencia práctica: Pillow es dependencia
   obligatoria (el crawl explota al arrancar sin ella) y las imágenes no son
   bit a bit las del sitio.
10. **Verificar el producto, no el proceso.** El exit code 0 y el print de
    resumen no dicen nada: el run del 14-oct murió a los 9 minutos (proceso
    matado, sin error en el log) y dejó un JSON truncado con 223 items y una
    DB a medio commitear. La verificación final fue leer el disco: 1000
    items, 1000 UPCs, 1000 imágenes, tipos correctos en JSON y DB.

## Notas del sitio (data quirks, no bugs)

- `robots.txt` devuelve 404: el sitio no lo tiene; Scrapy lo pide igual (1
  request extra por crawl).
- 152 de los 1000 libros tienen categoría "Default" en el breadcrumb del
  sitio (verificado contra el HTML real). El hermano solo vio 3 en su muestra
  de 40.
- Rango de precios en el sitio completo: £10.00 – £59.99.

## Decisiones de diseño

- **INSERT OR REPLACE por UPC**: correr el crawl de nuevo es seguro (pisa
  filas en vez de duplicar). A diferencia del `DELETE FROM` completo del
  hermano, una corrida interrumpida deja la DB útil.
- **`img_path` va al JSON, no a la DB**: la fila no depende de que la imagen
  haya bajado (el pipeline SQL corre después del de imágenes, pero no lee su
  resultado).
- **Duplicado (350) corre antes de Imágenes (380)**: un libro repetido no
  descarga su imagen dos veces.
- **availability queda bool y el número vive en stock int**: el hermano
  perdía el conteo "(19 available)" al convertir directo a bool.
- **Corrida completa ≈ 2051 requests en frío** (1 robots + 50 páginas + 1000
  detalles + 1000 imágenes); con imágenes ya en disco bajó a 1818 porque
  `ImagesPipeline` cachea por path.
