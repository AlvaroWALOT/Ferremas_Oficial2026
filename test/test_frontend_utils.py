from unittest.mock import patch

import app


def test_total_items_carrito():
    assert app.total_items_carrito({'1': 2, '2': 3}) == 5


def test_convertir_desde_clp():
    assert app.convertir_desde_clp(1000, 'CLP', 900) == 1000
    assert app.convertir_desde_clp(2000, 'USD', 1000) == 2.0


def test_construir_items_comprados():
    productos = [{'id': 1, 'nombre': 'Martillo', 'precio': 5000}]
    carrito = {'1': 2}

    items = app.construir_items_comprados(productos, carrito)

    assert items == [{
        'producto_id': 1,
        'nombre': 'Martillo',
        'cantidad': 2,
        'precio_unitario': 5000,
        'subtotal': 10000,
    }]


@patch('app.api_get')
def test_calcular_resumen_carrito_con_descuento(mock_api_get):
    mock_api_get.return_value = ([{'id': 1, 'precio': 2000}], None)

    with app.app.test_request_context('/'):
        app.session['usuario_logueado'] = True
        app.session['codigo_descuento_aplicado'] = app.DISCOUNT_CODE

        productos, subtotal, descuento, total = app.calcular_resumen_carrito({'1': 4})

    assert subtotal == 8000
    assert descuento == 800
    assert total == 7200
