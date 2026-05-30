"""
FERREMAS - Backend API
Puerto: 5001
Expone endpoints REST que acceden a la base de datos.
El frontend (app.py, puerto 5000) consume esta API.
"""
from flask import Flask, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from sqlalchemy import text
import json
import os
import sys

# Asegura que los módulos de este directorio se importen correctamente
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import db, Producto, Precio, CompraHistorial, Usuario
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)


# ─── Migración liviana de esquema ───────────────────────────────────────────
def ensure_schema():
    with db.engine.begin() as conn:
        # compra_historial columns
        tabla = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='compra_historial'"
        ))
        if tabla.fetchone():
            cols_info = conn.execute(text("PRAGMA table_info(compra_historial)"))
            cols = {row[1] for row in cols_info.fetchall()}
            if 'moneda' not in cols:
                conn.execute(text("ALTER TABLE compra_historial ADD COLUMN moneda VARCHAR(10) NOT NULL DEFAULT 'CLP'"))
            if 'tasa_cambio' not in cols:
                conn.execute(text("ALTER TABLE compra_historial ADD COLUMN tasa_cambio FLOAT NOT NULL DEFAULT 1.0"))
            if 'metodo_pago' not in cols:
                conn.execute(text("ALTER TABLE compra_historial ADD COLUMN metodo_pago VARCHAR(20) NOT NULL DEFAULT 'Tarjeta'"))
            if 'estado_pago' not in cols:
                conn.execute(text("ALTER TABLE compra_historial ADD COLUMN estado_pago VARCHAR(30) NOT NULL DEFAULT 'En Espera'"))
            if 'estado_pedido' not in cols:
                conn.execute(text("ALTER TABLE compra_historial ADD COLUMN estado_pedido VARCHAR(30) NOT NULL DEFAULT 'Pendiente'"))
            if 'metodo_entrega' not in cols:
                conn.execute(text("ALTER TABLE compra_historial ADD COLUMN metodo_entrega VARCHAR(30) NOT NULL DEFAULT 'Retiro en Tienda'"))
            if 'direccion_entrega' not in cols:
                conn.execute(text("ALTER TABLE compra_historial ADD COLUMN direccion_entrega VARCHAR(255)"))

        # usuario columns
        tabla_u = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='usuario'"
        ))
        if tabla_u.fetchone():
            cols_u = conn.execute(text("PRAGMA table_info(usuario)"))
            cols_u_set = {row[1] for row in cols_u.fetchall()}
            if 'rol' not in cols_u_set:
                conn.execute(text("ALTER TABLE usuario ADD COLUMN rol VARCHAR(20) NOT NULL DEFAULT 'cliente'"))


with app.app_context():
    db.create_all()
    ensure_schema()


# ─── Helpers ────────────────────────────────────────────────────────────────
def _serializar_producto(p):
    return {
        'id': p.id,
        'codigo_producto': p.codigo_producto,
        'marca': p.marca,
        'codigo_interno': p.codigo_interno,
        'nombre': p.nombre,
        'stock': p.stock,
        'imagen_url': p.imagen_url,
        'categoria': p.categoria,
        'destacado': p.destacado,
        'precio': p.precios[0].valor if p.precios else 0,
        'precios': [{'fecha': pr.fecha.isoformat(), 'valor': pr.valor} for pr in p.precios],
    }


def _serializar_compra(c):
    try:
        items = json.loads(c.detalle_items)
    except (json.JSONDecodeError, TypeError):
        items = []
    return {
        'id': c.id,
        'buy_order': c.buy_order,
        'usuario': c.usuario,
        'fecha': c.fecha.isoformat(),
        'metodo_pago': c.metodo_pago,
        'estado_pago': c.estado_pago,
        'estado_pedido': c.estado_pedido,
        'metodo_entrega': c.metodo_entrega,
        'direccion_entrega': c.direccion_entrega or '',
        'moneda': c.moneda,
        'tasa_cambio': c.tasa_cambio,
        'subtotal': c.subtotal,
        'descuento': c.descuento,
        'total': c.total,
        'items': items,
    }


# ════════════════════════════════════════════════════════════════════════════
#  PRODUCTOS
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/products', methods=['GET'])
def get_products():
    """Devuelve todos los productos con filtro opcional por categoría."""
    categoria = request.args.get('categoria')
    if categoria:
        productos = Producto.query.filter_by(categoria=categoria).all()
    else:
        productos = Producto.query.all()

    categorias = [
        c[0] for c in db.session.query(Producto.categoria).distinct().all() if c[0]
    ]
    return jsonify({
        'productos': [_serializar_producto(p) for p in productos],
        'categorias': categorias,
    })


@app.route('/api/products/destacados', methods=['GET'])
def get_destacados():
    """Devuelve hasta 4 productos marcados como destacados."""
    productos = Producto.query.filter_by(destacado=True).limit(4).all()
    return jsonify([_serializar_producto(p) for p in productos])


@app.route('/api/products/batch', methods=['GET'])
def get_products_batch():
    """Devuelve múltiples productos por IDs separados por coma: ?ids=1,2,3"""
    ids_str = request.args.get('ids', '')
    if not ids_str:
        return jsonify([])
    try:
        ids = [int(i) for i in ids_str.split(',') if i.strip()]
    except ValueError:
        return jsonify({'error': 'IDs inválidos'}), 400
    productos = Producto.query.filter(Producto.id.in_(ids)).all()
    return jsonify([_serializar_producto(p) for p in productos])


@app.route('/api/products/<int:producto_id>', methods=['GET'])
def get_product(producto_id):
    """Devuelve un producto por ID."""
    producto = Producto.query.get_or_404(producto_id)
    return jsonify(_serializar_producto(producto))


# ════════════════════════════════════════════════════════════════════════════
#  COMPRAS / HISTORIAL
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/compras/<usuario>', methods=['GET'])
def get_compras(usuario):
    """Historial de compras de un usuario. Auto-expira transferencias pendientes."""
    limite = datetime.utcnow() - timedelta(hours=1)
    CompraHistorial.query.filter(
        CompraHistorial.usuario == usuario,
        CompraHistorial.metodo_pago == 'Transferencia',
        CompraHistorial.estado_pago == 'En Espera',
        CompraHistorial.fecha < limite,
    ).update({'estado_pago': 'Rechazado'}, synchronize_session=False)
    db.session.commit()

    compras = CompraHistorial.query.filter_by(usuario=usuario).order_by(
        CompraHistorial.fecha.desc()
    ).all()
    return jsonify([_serializar_compra(c) for c in compras])


@app.route('/api/compras', methods=['POST'])
def crear_compra():
    """Crea un registro de compra. Body JSON con todos los campos."""
    data = request.get_json(silent=True) or {}
    compra = CompraHistorial(
        usuario=data.get('usuario', ''),
        buy_order=data.get('buy_order', ''),
        metodo_pago=data.get('metodo_pago', 'Tarjeta'),
        estado_pago=data.get('estado_pago', 'En Espera'),
        estado_pedido=data.get('estado_pedido', 'Pendiente'),
        metodo_entrega=data.get('metodo_entrega', 'Retiro en Tienda'),
        direccion_entrega=data.get('direccion_entrega', ''),
        moneda=data.get('moneda', 'CLP'),
        tasa_cambio=float(data.get('tasa_cambio', 1.0)),
        subtotal=int(data.get('subtotal', 0)),
        descuento=int(data.get('descuento', 0)),
        total=int(data.get('total', 0)),
        detalle_items=json.dumps(data.get('items', []), ensure_ascii=False),
    )
    db.session.add(compra)
    db.session.commit()
    return jsonify({'ok': True, 'id': compra.id}), 201


@app.route('/api/compras/<int:compra_id>/aprobar', methods=['PUT'])
def aprobar_compra(compra_id):
    """Aprueba una transferencia pendiente y descuenta el stock. Body JSON: {usuario}"""
    data = request.get_json(silent=True) or {}
    usuario = data.get('usuario', '')

    compra = CompraHistorial.query.filter_by(id=compra_id, usuario=usuario).first()
    if not compra:
        return jsonify({'ok': False, 'error': 'No se encontró la compra'}), 404

    if compra.metodo_pago != 'Transferencia':
        return jsonify({'ok': False, 'error': 'Solo transferencias se pueden aprobar manualmente'}), 400

    if compra.estado_pago == 'Aprobado':
        return jsonify({'ok': False, 'error': 'Esta transferencia ya estaba aprobada'}), 400

    try:
        items = json.loads(compra.detalle_items)
    except (json.JSONDecodeError, TypeError):
        return jsonify({'ok': False, 'error': 'No se pudo leer el detalle de la compra'}), 500

    # Verificar stock primero
    ajustes = []
    for item in items:
        producto_id = item.get('producto_id')
        cantidad = int(item.get('cantidad', 0))
        if not producto_id or cantidad <= 0:
            continue
        producto = Producto.query.get(producto_id)
        if not producto:
            return jsonify({'ok': False, 'error': f'Producto ID {producto_id} no encontrado'}), 404
        if producto.stock < cantidad:
            return jsonify({
                'ok': False,
                'error': f'Stock insuficiente para {producto.nombre}. Disponible: {producto.stock}, requerido: {cantidad}',
            }), 400
        ajustes.append((producto, cantidad))

    for producto, cantidad in ajustes:
        producto.stock -= cantidad

    compra.estado_pago = 'Aprobado'
    db.session.commit()
    return jsonify({'ok': True})


# ════════════════════════════════════════════════════════════════════════════
#  STOCK
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/stock/descontar', methods=['POST'])
def descontar_stock():
    """Descuenta stock tras un pago aprobado. Body JSON: {items: [{producto_id, cantidad}]}"""
    data = request.get_json(silent=True) or {}
    items = data.get('items', [])

    for item in items:
        producto_id = item.get('producto_id')
        cantidad = int(item.get('cantidad', 0))
        if not producto_id or cantidad <= 0:
            continue
        producto = Producto.query.get(producto_id)
        if producto and producto.stock >= cantidad:
            producto.stock -= cantidad

    db.session.commit()
    return jsonify({'ok': True})


# ════════════════════════════════════════════════════════════════════════════
#  ADMIN - STOCK
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/admin/productos', methods=['GET'])
def admin_get_productos():
    """Todos los productos para la vista de administración."""
    productos = Producto.query.all()
    return jsonify([_serializar_producto(p) for p in productos])


@app.route('/api/admin/stock', methods=['POST'])
def admin_update_stock():
    """Actualización masiva de stock. Body JSON: {updates: [{id, stock}]}"""
    data = request.get_json(silent=True) or {}
    actualizaciones = data.get('updates', [])
    errores = []

    for upd in actualizaciones:
        producto_id = upd.get('id')
        nuevo_stock = upd.get('stock')
        if producto_id is None or nuevo_stock is None:
            continue
        producto = Producto.query.get(producto_id)
        if producto:
            try:
                producto.stock = int(nuevo_stock)
            except (ValueError, TypeError):
                errores.append(f'Stock inválido para producto {producto_id}')

    db.session.commit()
    return jsonify({'ok': True, 'errores': errores})


# ════════════════════════════════════════════════════════════════════════════
#  AUTENTICACIÓN - login devuelve rol
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Verifica credenciales. Body JSON: {usuario, password}"""
    data = request.get_json(silent=True) or {}
    usuario_str = data.get('usuario', '').strip().lower()
    password = data.get('password', '').strip()

    if not usuario_str or not password:
        return jsonify({'ok': False, 'error': 'Credenciales requeridas'}), 400

    usuario_db = Usuario.query.filter(
        (Usuario.username == usuario_str) | (Usuario.email == usuario_str)
    ).first()

    if usuario_db and check_password_hash(usuario_db.password_hash, password):
        return jsonify({'ok': True, 'username': usuario_db.username, 'rol': usuario_db.rol})

    return jsonify({'ok': False, 'error': 'Credenciales inválidas'}), 401


@app.route('/api/auth/registro', methods=['POST'])
def registro():
    """Registra un nuevo usuario cliente. Body JSON: {username, email, password}"""
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip().lower()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()

    if not username or not email or not password:
        return jsonify({'ok': False, 'error': 'Todos los campos son obligatorios'}), 400

    if len(password) < 6:
        return jsonify({'ok': False, 'error': 'La contraseña debe tener al menos 6 caracteres'}), 400

    if Usuario.query.filter(
        (Usuario.username == username) | (Usuario.email == email)
    ).first():
        return jsonify({'ok': False, 'error': 'El usuario o correo ya está registrado'}), 409

    nuevo = Usuario(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        rol='cliente',
    )
    db.session.add(nuevo)
    db.session.commit()
    return jsonify({'ok': True, 'username': username, 'rol': 'cliente'}), 201


# ════════════════════════════════════════════════════════════════════════════
#  USUARIOS - gestión por admin
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/usuarios', methods=['GET'])
def listar_usuarios():
    """Lista todos los usuarios. Usado por el admin."""
    usuarios = Usuario.query.order_by(Usuario.creado_en.desc()).all()
    return jsonify([{
        'id': u.id,
        'username': u.username,
        'email': u.email,
        'rol': u.rol,
        'creado_en': u.creado_en.isoformat(),
    } for u in usuarios])


@app.route('/api/usuarios/<int:uid>/rol', methods=['PUT'])
def cambiar_rol(uid):
    """Cambia el rol de un usuario. Body JSON: {rol}"""
    data = request.get_json(silent=True) or {}
    nuevo_rol = data.get('rol', '').strip().lower()
    roles_validos = {'cliente', 'admin', 'vendedor', 'bodeguero', 'contador'}
    if nuevo_rol not in roles_validos:
        return jsonify({'ok': False, 'error': f'Rol inválido. Válidos: {roles_validos}'}), 400
    usuario = Usuario.query.get_or_404(uid)
    usuario.rol = nuevo_rol
    db.session.commit()
    return jsonify({'ok': True, 'username': usuario.username, 'rol': usuario.rol})


# ════════════════════════════════════════════════════════════════════════════
#  PEDIDOS - workflow vendedor → bodeguero → contador
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/pedidos', methods=['GET'])
def listar_pedidos():
    """Todos los pedidos. Parámetros opcionales: estado_pedido, estado_pago, metodo_entrega"""
    estado_pedido = request.args.get('estado_pedido')
    estado_pago = request.args.get('estado_pago')
    metodo_entrega = request.args.get('metodo_entrega')

    q = CompraHistorial.query
    if estado_pedido:
        q = q.filter_by(estado_pedido=estado_pedido)
    if estado_pago:
        q = q.filter_by(estado_pago=estado_pago)
    if metodo_entrega:
        q = q.filter_by(metodo_entrega=metodo_entrega)

    pedidos = q.order_by(CompraHistorial.fecha.desc()).all()
    return jsonify([_serializar_compra(p) for p in pedidos])


def _cambiar_estado_pedido(compra_id, nuevo_estado, estados_validos_origen=None, extra_fn=None):
    """Helper genérico para cambiar estado_pedido."""
    compra = CompraHistorial.query.get(compra_id)
    if not compra:
        return jsonify({'ok': False, 'error': 'Pedido no encontrado'}), 404
    if estados_validos_origen and compra.estado_pedido not in estados_validos_origen:
        return jsonify({
            'ok': False,
            'error': f'El pedido está en estado "{compra.estado_pedido}", no se puede cambiar a "{nuevo_estado}"'
        }), 400
    compra.estado_pedido = nuevo_estado
    if extra_fn:
        result = extra_fn(compra)
        if result:
            return result
    db.session.commit()
    return jsonify({'ok': True, 'estado_pedido': nuevo_estado})


@app.route('/api/pedidos/<int:compra_id>/aprobar', methods=['PUT'])
def vendedor_aprobar(compra_id):
    """Vendedor aprueba el pedido → pasa a 'Aprobado'."""
    return _cambiar_estado_pedido(compra_id, 'Aprobado', estados_validos_origen=['Pendiente'])


@app.route('/api/pedidos/<int:compra_id>/rechazar', methods=['PUT'])
def vendedor_rechazar(compra_id):
    """Vendedor rechaza el pedido → pasa a 'Rechazado'."""
    return _cambiar_estado_pedido(compra_id, 'Rechazado', estados_validos_origen=['Pendiente'])


@app.route('/api/pedidos/<int:compra_id>/preparar', methods=['PUT'])
def bodeguero_preparar(compra_id):
    """Bodeguero acepta y comienza a preparar → 'En Preparacion'."""
    return _cambiar_estado_pedido(compra_id, 'En Preparacion', estados_validos_origen=['Aprobado'])


@app.route('/api/pedidos/<int:compra_id>/listo', methods=['PUT'])
def bodeguero_listo(compra_id):
    """Bodeguero marca el pedido como listo para entrega → 'Listo para Entrega'."""
    return _cambiar_estado_pedido(compra_id, 'Listo para Entrega', estados_validos_origen=['En Preparacion'])


@app.route('/api/pedidos/<int:compra_id>/entregar', methods=['PUT'])
def contador_entregar(compra_id):
    """Contador registra la entrega del producto al cliente → 'Entregado'."""
    return _cambiar_estado_pedido(compra_id, 'Entregado', estados_validos_origen=['Listo para Entrega'])


@app.route('/api/pedidos/<int:compra_id>/confirmar_pago', methods=['PUT'])
def contador_confirmar_pago(compra_id):
    """Contador confirma el pago por transferencia → estado_pago 'Aprobado'."""
    compra = CompraHistorial.query.get(compra_id)
    if not compra:
        return jsonify({'ok': False, 'error': 'Pedido no encontrado'}), 404
    if compra.metodo_pago != 'Transferencia':
        return jsonify({'ok': False, 'error': 'Solo transferencias requieren confirmación manual'}), 400
    if compra.estado_pago == 'Aprobado':
        return jsonify({'ok': False, 'error': 'El pago ya fue confirmado anteriormente'}), 400
    compra.estado_pago = 'Aprobado'
    db.session.commit()
    return jsonify({'ok': True})


# ════════════════════════════════════════════════════════════════════════════
#  REPORTES - admin
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/reportes/ventas', methods=['GET'])
def reporte_ventas():
    """Resumen de ventas. Parámetros opcionales: mes (1-12), anio (4 dígitos)."""
    from datetime import date
    mes = request.args.get('mes', type=int)
    anio = request.args.get('anio', type=int, default=date.today().year)

    q = CompraHistorial.query.filter(CompraHistorial.estado_pago == 'Aprobado')
    if anio:
        q = q.filter(db.extract('year', CompraHistorial.fecha) == anio)
    if mes:
        q = q.filter(db.extract('month', CompraHistorial.fecha) == mes)

    compras = q.order_by(CompraHistorial.fecha.desc()).all()

    total_ventas = sum(c.total for c in compras)
    total_descuentos = sum(c.descuento for c in compras)

    # Ventas por método de pago
    por_metodo = {}
    for c in compras:
        por_metodo[c.metodo_pago] = por_metodo.get(c.metodo_pago, 0) + c.total

    # Ventas por método de entrega
    por_entrega = {}
    for c in compras:
        por_entrega[c.metodo_entrega] = por_entrega.get(c.metodo_entrega, 0) + 1

    return jsonify({
        'anio': anio,
        'mes': mes,
        'cantidad_ordenes': len(compras),
        'total_ventas_clp': total_ventas,
        'total_descuentos_clp': total_descuentos,
        'por_metodo_pago': por_metodo,
        'por_metodo_entrega': por_entrega,
        'ordenes': [_serializar_compra(c) for c in compras],
    })


# ════════════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    app.run(port=5001, debug=True)
