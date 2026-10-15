from books_scrapy.pipelines import parse_price


def test_precio_libra_estandar():
    assert parse_price("£51.77") == 51.77


def test_precio_con_coma_decimal_europea():
    # "£51,77" termina en ",77" -> la coma es decimal
    assert parse_price("£51,77") == 51.77


def test_precio_vacio():
    assert parse_price("") is None
    assert parse_price(None) is None


def test_precio_sin_digitos():
    assert parse_price("N/A") is None
    assert parse_price("Gratis") is None


def test_formato_europeo_miles_y_decimal():
    # coma despues del punto: coma es decimal, punto es miles
    assert parse_price("£1.234,56") == 1234.56


def test_formato_us_miles_y_decimal():
    # punto despues de la coma: coma es miles
    assert parse_price("£1,234.56") == 1234.56


def test_coma_de_miles_sin_decimales():
    # "£1,234" no termina en ",NN" -> coma es miles
    assert parse_price("£1,234") == 1234.0
