from unittest.mock import patch

import app


@patch('app.api_get')
@patch('app.crear_transaccion')
def test_pagar_con_tarjeta_redirecciona_webpay(mock_crear_transaccion, mock_api_get):
    mock_api_get.return_value = ([{'id': 1, 'precio': 1000}], None)
    mock_transaction = mock_crear_transaccion.return_value
    mock_transaction.create.return_value = {
        'url': 'https://webpay.test/redirect',
        'token': 'TOK123'
    }

    with app.app.test_client() as client:
        with client.session_transaction() as sess:
            sess['carrito'] = {'1': 1}
            sess['moneda_seleccionada'] = 'CLP'
            sess['tasa_moneda'] = 1.0
            sess['usuario_logueado'] = True
            sess['usuario_nombre'] = 'cliente1'

        response = client.post('/pagar', data={'metodo_pago': 'tarjeta', 'metodo_entrega': 'Retiro en Tienda'})

    assert response.status_code == 302
    assert response.headers['Location'].startswith('https://webpay.test/redirect?token_ws=TOK123')
    mock_transaction.create.assert_called_once()


@patch('app.api_get')
@patch('app.api_post')
def test_pagar_con_transferencia_renderiza_transferencia(mock_api_post, mock_api_get):
    mock_api_get.return_value = ([{'id': 1, 'precio': 2000, 'nombre': 'Martillo'}], None)

    with app.app.test_client() as client:
        with client.session_transaction() as sess:
            sess['carrito'] = {'1': 2}
            sess['moneda_seleccionada'] = 'CLP'
            sess['tasa_moneda'] = 1.0
            sess['usuario_logueado'] = True
            sess['usuario_nombre'] = 'cliente1'

        response = client.post('/pagar', data={
            'metodo_pago': 'transferencia',
            'metodo_entrega': 'Retiro en Tienda',
            'direccion_entrega': '',
        })

    assert response.status_code == 200
    assert b'Referencia' in response.data or b'referencia' in response.data
    mock_api_post.assert_called_once()


def test_confirmar_pago_sin_token_redirecciona():
    with app.app.test_client() as client:
        response = client.get('/confirmar_pago')

    assert response.status_code == 302
    assert '/carrito' in response.headers['Location']


@patch('app.api_get')
@patch('app.api_post')
@patch('app.crear_transaccion')
def test_confirmar_pago_autorizado_registra_compra(mock_crear_transaccion, mock_api_post, mock_api_get):
    mock_api_get.return_value = ([{'id': 1, 'precio': 1500, 'nombre': 'Martillo'}], None)
    mock_transaction = mock_crear_transaccion.return_value
    mock_transaction.commit.return_value = {
        'status': 'AUTHORIZED',
        'buy_order': '123456'
    }

    with app.app.test_client() as client:
        with client.session_transaction() as sess:
            sess['carrito'] = {'1': 1}
            sess['moneda_compra'] = 'CLP'
            sess['tasa_compra'] = 1.0
            sess['metodo_entrega'] = 'Retiro en Tienda'
            sess['direccion_entrega'] = ''
            sess['usuario_logueado'] = True
            sess['usuario_nombre'] = 'cliente1'

        response = client.get('/confirmar_pago?token_ws=TOK123')

    assert response.status_code == 200
    assert b'Monto:' in response.data or b'Estado:' in response.data
    assert mock_api_post.call_count >= 1
    mock_transaction.commit.assert_called_once_with('TOK123')


@patch('app.api_get')
@patch('app.api_post')
@patch('app.crear_transaccion')
def test_confirmar_pago_rechazado_redirecciona_carrito(mock_crear_transaccion, mock_api_post, mock_api_get):
    mock_api_get.return_value = ([{'id': 1, 'precio': 1500, 'nombre': 'Martillo'}], None)
    mock_transaction = mock_crear_transaccion.return_value
    mock_transaction.commit.return_value = {
        'status': 'REJECTED',
        'buy_order': '654321'
    }

    with app.app.test_client() as client:
        with client.session_transaction() as sess:
            sess['carrito'] = {'1': 1}
            sess['moneda_compra'] = 'CLP'
            sess['tasa_compra'] = 1.0
            sess['metodo_entrega'] = 'Retiro en Tienda'
            sess['direccion_entrega'] = ''
            sess['usuario_logueado'] = True
            sess['usuario_nombre'] = 'cliente1'

        response = client.get('/confirmar_pago?token_ws=TOK123')

    assert response.status_code == 302
    assert '/carrito' in response.headers['Location']
    mock_transaction.commit.assert_called_once_with('TOK123')
    mock_api_post.assert_called()
