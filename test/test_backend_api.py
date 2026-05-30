import json
from datetime import datetime


def test_get_products_empty(backend_client):
    response = backend_client.get('/api/products')
    assert response.status_code == 200
    data = response.get_json()
    assert data['productos'] == []
    assert data['categorias'] == []


def test_product_crud_and_batch(backend_app, backend_client):
    with backend_app.app.app_context():
        producto = backend_app.Producto(
            codigo_producto='P001',
            codigo_interno='INT001',
            nombre='Martillo',
            stock=10,
            categoria='Herramientas',
            destacado=True,
        )
        backend_app.db.session.add(producto)
        backend_app.db.session.commit()
        producto_id = producto.id

        precio = backend_app.Precio(
            producto_id=producto_id,
            fecha=datetime.utcnow(),
            valor=15990,
        )
        backend_app.db.session.add(precio)
        backend_app.db.session.commit()

    response = backend_client.get('/api/products')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data['productos']) == 1
    assert data['categorias'] == ['Herramientas']

    response = backend_client.get(f'/api/products/{producto_id}')
    assert response.status_code == 200
    assert response.get_json()['nombre'] == 'Martillo'

    response = backend_client.get(f'/api/products/batch?ids={producto_id}')
    assert response.status_code == 200
    batch_data = response.get_json()
    assert isinstance(batch_data, list)
    assert batch_data[0]['id'] == producto_id


def test_crear_compra(backend_client):
    payload = {
        'usuario': 'cliente1',
        'buy_order': '012345',
        'metodo_pago': 'Transferencia',
        'estado_pago': 'En Espera',
        'estado_pedido': 'Pendiente',
        'metodo_entrega': 'Retiro en Tienda',
        'direccion_entrega': 'Av. Principal 123',
        'moneda': 'CLP',
        'tasa_cambio': 1.0,
        'subtotal': 10000,
        'descuento': 0,
        'total': 10000,
        'items': [{'producto_id': 1, 'nombre': 'Martillo', 'cantidad': 1, 'precio_unitario': 10000, 'subtotal': 10000}],
    }

    response = backend_client.post('/api/compras', json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data['ok'] is True
    assert data['id'] > 0

    response = backend_client.get('/api/compras/cliente1')
    assert response.status_code == 200
    compra_data = response.get_json()
    assert len(compra_data) == 1
    assert compra_data[0]['usuario'] == 'cliente1'
