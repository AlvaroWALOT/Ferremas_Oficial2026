import json
import random
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


def create_product(backend_app, codigo='P002', nombre='Destornillador', stock=10, categoria='Herramientas'):
    with backend_app.app.app_context():
        producto = backend_app.Producto(
            codigo_producto=codigo,
            codigo_interno=f'INT-{codigo}',
            nombre=nombre,
            stock=stock,
            categoria=categoria,
            destacado=False,
        )
        backend_app.db.session.add(producto)
        backend_app.db.session.commit()
        backend_app.db.session.add(backend_app.Precio(
            producto_id=producto.id,
            fecha=datetime.utcnow(),
            valor=5000,
        ))
        backend_app.db.session.commit()
        return producto.id


def create_compra(backend_app, metodo_pago='Tarjeta', estado_pago='En Espera', estado_pedido='Pendiente', metodo_entrega='Retiro en Tienda', usuario='cliente1', total=10000):
    with backend_app.app.app_context():
        compra = backend_app.CompraHistorial(
            usuario=usuario,
            buy_order='ORD-' + str(random.randint(100000, 999999)),
            metodo_pago=metodo_pago,
            estado_pago=estado_pago,
            estado_pedido=estado_pedido,
            metodo_entrega=metodo_entrega,
            direccion_entrega='Av. Test 123',
            moneda='CLP',
            tasa_cambio=1.0,
            subtotal=total,
            descuento=0,
            total=total,
            detalle_items=json.dumps([{'producto_id': 1, 'nombre': 'Martillo', 'cantidad': 1, 'precio_unitario': total, 'subtotal': total}]),
        )
        backend_app.db.session.add(compra)
        backend_app.db.session.commit()
        return compra.id


def test_descontar_stock(backend_app, backend_client):
    producto_id = create_product(backend_app, stock=10)

    response = backend_client.post('/api/stock/descontar', json={'items': [{'producto_id': producto_id, 'cantidad': 3}]})
    assert response.status_code == 200
    assert response.get_json() == {'ok': True}

    with backend_app.app.app_context():
        producto = backend_app.Producto.query.get(producto_id)
        assert producto.stock == 7


def test_vendedor_aprobar_pedido(backend_app, backend_client):
    compra_id = create_compra(backend_app, metodo_pago='Tarjeta', estado_pedido='Pendiente')

    response = backend_client.put(f'/api/pedidos/{compra_id}/aprobar')
    assert response.status_code == 200
    assert response.get_json() == {'ok': True, 'estado_pedido': 'Aprobado'}

    with backend_app.app.app_context():
        compra = backend_app.CompraHistorial.query.get(compra_id)
        assert compra.estado_pedido == 'Aprobado'


def test_contador_confirmar_pago_transferencia(backend_app, backend_client):
    compra_id = create_compra(backend_app, metodo_pago='Transferencia', estado_pago='En Espera')

    response = backend_client.put(f'/api/pedidos/{compra_id}/confirmar_pago')
    assert response.status_code == 200
    assert response.get_json() == {'ok': True}

    with backend_app.app.app_context():
        compra = backend_app.CompraHistorial.query.get(compra_id)
        assert compra.estado_pago == 'Aprobado'


def test_reporte_ventas_incluye_solo_aprobados(backend_app, backend_client):
    create_compra(backend_app, metodo_pago='Tarjeta', estado_pago='Aprobado', total=12000)
    create_compra(backend_app, metodo_pago='Transferencia', estado_pago='En Espera', total=8000)

    response = backend_client.get('/api/reportes/ventas')
    assert response.status_code == 200

    data = response.get_json()
    assert data['cantidad_ordenes'] == 1
    assert data['total_ventas_clp'] == 12000
    assert data['por_metodo_pago']['Tarjeta'] == 12000
    assert data['por_metodo_entrega']['Retiro en Tienda'] == 1
