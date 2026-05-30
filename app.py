"""
FERREMAS - Frontend Web
Puerto: 5000
Sirve las páginas HTML y llama al Backend API (puerto 5001) para datos de BD.
Si el backend no está disponible, la web sigue funcionando con datos vacíos.
"""
from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
import json
import os
from datetime import datetime
import requests as http
import smtplib
from email.message import EmailMessage
from services.currency import obtener_tipo_cambio

app = Flask(__name__)
app.secret_key = 'clave-secreta-ferremas'

# URL del backend API. Se puede cambiar con variable de entorno BACKEND_URL
BACKEND_URL = os.environ.get('BACKEND_URL', 'http://localhost:5001')


# ─── Cliente HTTP hacia el backend ──────────────────────────────────────────
def api_get(endpoint, params=None):
    """GET al backend. Devuelve (datos, error_msg)."""
    try:
        r = http.get(f"{BACKEND_URL}{endpoint}", params=params, timeout=5)
        r.raise_for_status()
        return r.json(), None
    except http.exceptions.ConnectionError:
        return None, "El servicio de base de datos no está disponible"
    except http.exceptions.Timeout:
        return None, "Tiempo de espera agotado"
    except Exception as e:
        return None, str(e)


def api_post(endpoint, payload):
    """POST al backend. Devuelve (datos, error_msg)."""
    try:
        r = http.post(f"{BACKEND_URL}{endpoint}", json=payload, timeout=5)
        r.raise_for_status()
        return r.json(), None
    except http.exceptions.ConnectionError:
        return None, "El servicio de base de datos no está disponible"
    except http.exceptions.Timeout:
        return None, "Tiempo de espera agotado"
    except Exception as e:
        return None, str(e)


def api_put(endpoint, payload):
    """PUT al backend. Devuelve (datos, error_msg)."""
    try:
        r = http.put(f"{BACKEND_URL}{endpoint}", json=payload, timeout=5)
        r.raise_for_status()
        return r.json(), None
    except http.exceptions.ConnectionError:
        return None, "El servicio de base de datos no está disponible"
    except http.exceptions.Timeout:
        return None, "Tiempo de espera agotado"
    except Exception as e:
        return None, str(e)

DISCOUNT_CODE = 'FERREMAS'
DISCOUNT_PERCENT = 0.10
VALID_USERS = {
    'cliente': '1234'
}

DATOS_TRANSFERENCIA = {
    'nombre': 'Alvaro CASTRO',
    'rut': '20.099.314-4',
    'email': 'alvarocastro607@gmail.com',
    'tipo_cuenta': 'Cuenta Corriente',
    'numero_cuenta': '15841000915',
    'banco': 'Banco Falabella'
}

SMTP_CONFIG = {
    'host': 'smtp.gmail.com',
    'port': 587,
    'user': 'alvaro.castro@chepss.com',
    'from': 'alvaro.castro@chepss.com',
    'password': 'tupwblirabmukqjt',
    'use_tls': True
}


@app.context_processor
def inject_session_user():
    return {
        'usuario_logueado': session.get('usuario_logueado', False),
        'usuario_nombre': session.get('usuario_nombre', ''),
        'usuario_rol': session.get('usuario_rol', 'cliente'),
    }


def total_items_carrito(carrito):
    """Devuelve la suma total de unidades en el carrito."""
    return sum(int(v) for v in carrito.values()) if carrito else 0


def enviar_correo_bienvenida(destinatario, usuario):
    smtp_host = SMTP_CONFIG['host']
    smtp_port = int(SMTP_CONFIG['port'])
    smtp_user = SMTP_CONFIG['user']
    smtp_password = SMTP_CONFIG['password']
    smtp_from = SMTP_CONFIG['from']
    smtp_use_tls = bool(SMTP_CONFIG['use_tls'])

    mensaje = EmailMessage()
    mensaje['Subject'] = 'Bienvenido a FERREMAS'
    mensaje['From'] = smtp_from
    mensaje['To'] = destinatario
    mensaje.set_content(
        f"Hola {usuario},\n\n"
        "Tu cuenta en FERREMAS fue creada correctamente.\n"
        "Felicitaciones y gracias por registrarte con nosotros.\n\n"
        "Equipo FERREMAS"
    )

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            if smtp_use_tls:
                server.starttls()
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.send_message(mensaje)
        return True
    except Exception:
        return False


def calcular_resumen_carrito(carrito):
    """Calcula subtotal, descuento y total consultando el backend API."""
    if not carrito:
        return [], 0, 0, 0

    ids_str = ','.join(str(pid) for pid in carrito.keys())
    datos, error = api_get('/api/products/batch', params={'ids': ids_str})
    if error or not datos:
        return [], 0, 0, 0

    productos = datos
    subtotal = 0
    for producto in productos:
        precio = producto.get('precio', 0)
        cantidad = carrito.get(str(producto['id']), 0)
        subtotal += precio * cantidad

    # Descuento: requiere cupón FERREMAS + mínimo 4 unidades en total
    descuento = 0
    unidades_totales = total_items_carrito(carrito)
    if (session.get('usuario_logueado')
            and session.get('codigo_descuento_aplicado') == DISCOUNT_CODE
            and unidades_totales >= 4):
        descuento = int(subtotal * DISCOUNT_PERCENT)

    total = int(subtotal - descuento)
    return productos, int(subtotal), descuento, total


def convertir_desde_clp(monto_clp, moneda, tasa_cambio):
    if moneda == 'CLP' or not tasa_cambio:
        return int(monto_clp)
    return round(float(monto_clp) / float(tasa_cambio), 2)


def construir_items_comprados(productos, carrito):
    items = []
    for producto in productos:
        cantidad = carrito.get(str(producto['id']), 0)
        precio = int(producto.get('precio', 0))

        if cantidad > 0:
            items.append({
                'producto_id': producto['id'],
                'nombre': producto['nombre'],
                'cantidad': cantidad,
                'precio_unitario': precio,
                'subtotal': int(precio * cantidad)
            })

    return items


@app.route("/")
def index():
    datos, _ = api_get('/api/products/destacados')
    productos_destacados = datos if datos else []
    return render_template("index.html", productos=productos_destacados)


@app.route("/contact", methods=["GET", "POST"])
def contact():
    mensaje = None
    if request.method == "POST":
        nombre = request.form["nombre"]
        email = request.form["email"]
        contenido = request.form["mensaje"]
        mensaje = "¡Gracias por contactarnos, te responderemos pronto!"

    return render_template("contact.html", mensaje=mensaje)


@app.route('/tienda')
def tienda():
    moneda = request.args.get('moneda', 'CLP')
    tasa = 1

    if moneda != 'CLP':
        tasa_api = obtener_tipo_cambio(moneda)
        if tasa_api:
            tasa = tasa_api

    categoria = request.args.get('categoria')
    datos, error = api_get('/api/products', params={'categoria': categoria} if categoria else None)

    if error:
        flash(f"No se pudieron cargar los productos: {error}", "warning")
        productos = []
        categorias = []
    else:
        productos = datos.get('productos', [])
        categorias = datos.get('categorias', [])

    session['moneda_seleccionada'] = moneda
    session['tasa_moneda'] = float(tasa)

    return render_template(
        'tienda.html',
        productos=productos,
        categorias=categorias,
        categoria_seleccionada=categoria,
        moneda=moneda,
        tasa=tasa
    )


@app.route('/agregar_al_carrito/<int:producto_id>', methods=['POST'])
def agregar_al_carrito(producto_id):
    cantidad_solicitada = int(request.form.get('cantidad', 1))

    producto, error = api_get(f'/api/products/{producto_id}')
    if error or not producto:
        return jsonify({"success": False, "mensaje": "Producto no disponible en este momento."})

    carrito = session.get('carrito', {})
    cantidad_actual = carrito.get(str(producto_id), 0)

    stock_disponible = producto['stock'] - cantidad_actual
    if stock_disponible <= 0:
        return jsonify({
            "success": False,
            "mensaje": f"No hay stock disponible para '{producto['nombre']}'."
        })

    cantidad_a_agregar = min(cantidad_solicitada, stock_disponible)
    carrito[str(producto_id)] = cantidad_actual + cantidad_a_agregar
    session['carrito'] = carrito

    if cantidad_a_agregar < cantidad_solicitada:
        mensaje = f"Solo se agregaron {cantidad_a_agregar} unidades de '{producto['nombre']}' por stock limitado."
    else:
        mensaje = f"Producto '{producto['nombre']}' agregado al carrito."

    return jsonify({
        "success": True,
        "mensaje": mensaje
    })





@app.route('/carrito')
def ver_carrito():
    raw_carrito = session.get('carrito', {})
    carrito = {int(k): v for k, v in raw_carrito.items()}  # convierte claves a enteros

    productos, subtotal, descuento, total = calcular_resumen_carrito(raw_carrito)

    return render_template(
        'carrito.html',
        productos=productos,
        carrito=carrito,
        subtotal=subtotal,
        descuento=descuento,
        total=total,
        usuario_logueado=session.get('usuario_logueado', False),
        usuario_nombre=session.get('usuario_nombre', ''),
        codigo_descuento_aplicado=session.get('codigo_descuento_aplicado')
    )


@app.route('/login', methods=['POST'])
def login():
    usuario = request.form.get('usuario', '').strip().lower()
    password = request.form.get('password', '').strip()

    datos, error = api_post('/api/auth/login', {'usuario': usuario, 'password': password})

    if not error and datos and datos.get('ok'):
        session['usuario_logueado'] = True
        session['usuario_nombre'] = datos['username']
        session['usuario_rol'] = datos.get('rol', 'cliente')
        flash('Sesion iniciada correctamente.', 'success')
        return _redirect_por_rol(datos.get('rol', 'cliente'))

    # Fallback: usuarios hardcodeados locales (funciona sin backend)
    if usuario in VALID_USERS and VALID_USERS[usuario] == password:
        session['usuario_logueado'] = True
        session['usuario_nombre'] = usuario
        session['usuario_rol'] = 'cliente'
        flash('Sesion iniciada correctamente.', 'success')
    else:
        if error:
            flash(f'No se pudo conectar con el servidor. ({error})', 'danger')
        else:
            flash('Credenciales invalidas.', 'danger')

    return redirect(url_for('ver_carrito'))


def _redirect_por_rol(rol):
    """Redirige al dashboard según el rol del usuario."""
    destinos = {
        'admin': 'dashboard_admin',
        'vendedor': 'dashboard_vendedor',
        'bodeguero': 'dashboard_bodeguero',
        'contador': 'dashboard_contador',
    }
    if rol in destinos:
        return redirect(url_for(destinos[rol]))
    return redirect(url_for('ver_carrito'))


@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        datos, error = api_post('/api/auth/registro', {
            'username': username,
            'email': email,
            'password': password,
        })

        if error:
            flash(f'No se pudo registrar: {error}', 'danger')
            return redirect(url_for('registro'))

        if not datos or not datos.get('ok'):
            flash(datos.get('error', 'Error al registrar.'), 'danger')
            return redirect(url_for('registro'))

        correo_enviado = enviar_correo_bienvenida(email, username)
        if correo_enviado:
            flash('Cuenta creada correctamente. Te enviamos un correo de felicitaciones.', 'success')
        else:
            flash('Cuenta creada correctamente. No se pudo enviar el correo (SMTP no configurado).', 'info')

        return redirect(url_for('ver_carrito'))

    return render_template('registro.html')


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('usuario_logueado', None)
    session.pop('usuario_nombre', None)
    session.pop('usuario_rol', None)
    session.pop('codigo_descuento_aplicado', None)
    flash('Sesion cerrada.', 'info')
    return redirect(url_for('ver_carrito'))


@app.route('/aplicar_descuento', methods=['POST'])
def aplicar_descuento():
    if not session.get('usuario_logueado'):
        flash('Debes iniciar sesion para aplicar descuentos.', 'warning')
        return redirect(url_for('ver_carrito'))

    codigo = request.form.get('codigo_descuento', '').strip().upper()

    if codigo != DISCOUNT_CODE:
        session.pop('codigo_descuento_aplicado', None)
        flash('El código de descuento ingresado no es válido. Verifique e intente nuevamente.', 'danger')
        return redirect(url_for('ver_carrito'))

    # Verificar cantidad mínima de 4 unidades en el carrito
    carrito = session.get('carrito', {})
    unidades = total_items_carrito(carrito)
    if unidades < 4:
        flash(
            f'El cupón FERREMAS requiere un mínimo de 4 unidades en el carrito '
            f'(puedes combinar productos distintos o repetir el mismo). '
            f'Actualmente tienes {unidades} unidad{"" if unidades == 1 else "es"}.',
            'warning'
        )
        return redirect(url_for('ver_carrito'))

    session['codigo_descuento_aplicado'] = DISCOUNT_CODE
    flash('Código FERREMAS aplicado: 10% de descuento en tu compra.', 'success')
    return redirect(url_for('ver_carrito'))


@app.route('/mi-perfil')
def mi_perfil():
    if not session.get('usuario_logueado'):
        flash('Debes iniciar sesion para ver tu perfil.', 'warning')
        return redirect(url_for('ver_carrito'))

    usuario = session.get('usuario_nombre')
    compras_raw, error = api_get(f'/api/compras/{usuario}')

    if error:
        flash(f'No se pudo cargar el historial: {error}', 'warning')
        compras_raw = []

    compras = []
    for compra in (compras_raw or []):
        moneda = compra.get('moneda', 'CLP')
        tasa = float(compra.get('tasa_cambio', 1.0))
        # Convertir fecha ISO string → datetime para que el template pueda usar .strftime()
        try:
            fecha_dt = datetime.fromisoformat(compra['fecha'])
        except (ValueError, TypeError):
            fecha_dt = datetime.utcnow()

        compras.append({
            'id': compra['id'],
            'buy_order': compra['buy_order'],
            'fecha': fecha_dt,
            'metodo_pago': compra['metodo_pago'],
            'estado_pago': compra['estado_pago'],
            'moneda': moneda,
            'tasa_cambio': tasa,
            'subtotal': convertir_desde_clp(compra['subtotal'], moneda, tasa),
            'descuento': convertir_desde_clp(compra['descuento'], moneda, tasa),
            'total': convertir_desde_clp(compra['total'], moneda, tasa),
            'detalle_items': [
                {
                    'nombre': item.get('nombre'),
                    'cantidad': item.get('cantidad', 0),
                    'precio_unitario': convertir_desde_clp(item.get('precio_unitario', 0), moneda, tasa),
                    'subtotal': convertir_desde_clp(item.get('subtotal', 0), moneda, tasa),
                }
                for item in compra.get('items', [])
            ],
        })

    return render_template('perfil.html', compras=compras)


@app.route('/aprobar-transferencia/<int:compra_id>', methods=['POST'])
def aprobar_transferencia(compra_id):
    if not session.get('usuario_logueado'):
        flash('Debes iniciar sesion para gestionar pagos.', 'warning')
        return redirect(url_for('ver_carrito'))

    usuario = session.get('usuario_nombre')
    datos, error = api_put(f'/api/compras/{compra_id}/aprobar', {'usuario': usuario})

    if error:
        flash(f'No se pudo aprobar la transferencia: {error}', 'danger')
    elif not datos or not datos.get('ok'):
        flash(datos.get('error', 'Error al aprobar la transferencia.'), 'warning')
    else:
        flash('Transferencia marcada como aprobada.', 'success')

    return redirect(url_for('mi_perfil'))



@app.route('/eliminar/<int:producto_id>', methods=['POST'])
def eliminar_del_carrito(producto_id):
    carrito = session.get('carrito', {})
    producto_id_str = str(producto_id)

    if producto_id_str in carrito:
        if carrito[producto_id_str] > 1:
            carrito[producto_id_str] -= 1
        else:
            del carrito[producto_id_str]

    session['carrito'] = carrito
    return redirect(url_for('ver_carrito'))


@app.route('/remover/<int:producto_id>', methods=['POST'])
def remover_producto(producto_id):
    carrito = session.get('carrito', {})
    producto_id_str = str(producto_id)

    if producto_id_str in carrito:
        del carrito[producto_id_str]

    session['carrito'] = carrito
    return redirect(url_for('ver_carrito'))


@app.route('/vaciar', methods=['POST'])
def vaciar_carrito():
    session.pop('carrito', None)
    return redirect(url_for('ver_carrito'))

@app.route('/sumar/<int:producto_id>', methods=['POST'])
def sumar_producto(producto_id):
    carrito = session.get('carrito', {})
    producto_id_str = str(producto_id)
    if producto_id_str in carrito:
        carrito[producto_id_str] += 1
    else:
        carrito[producto_id_str] = 1
    session['carrito'] = carrito
    return redirect(url_for('ver_carrito'))

# Api Transbank
from transbank_config import crear_transaccion
import random


@app.route('/pagar', methods=['POST'])
def pagar():
    carrito = session.get('carrito', {})
    productos, subtotal, descuento, total = calcular_resumen_carrito(carrito)

    if total <= 0:
        flash("No puedes pagar un carrito vacío o sin precios válidos", "warning")
        return redirect(url_for('ver_carrito'))

    metodo_pago = request.form.get('metodo_pago', 'tarjeta').strip().lower()
    metodo_entrega = request.form.get('metodo_entrega', 'Retiro en Tienda').strip()
    direccion_entrega = request.form.get('direccion_entrega', '').strip()
    moneda_compra = session.get('moneda_seleccionada', 'CLP')
    tasa_compra = float(session.get('tasa_moneda', 1.0))

    # Validar dirección si eligió despacho
    if metodo_entrega == 'Despacho a Domicilio' and not direccion_entrega:
        flash('Debes ingresar una dirección para el despacho a domicilio.', 'warning')
        return redirect(url_for('ver_carrito'))

    # Guardar en sesión para usar en confirmar_pago
    session['metodo_entrega'] = metodo_entrega
    session['direccion_entrega'] = direccion_entrega

    if metodo_pago == 'transferencia':
        total_moneda = convertir_desde_clp(total, moneda_compra, tasa_compra)
        subtotal_moneda = convertir_desde_clp(subtotal, moneda_compra, tasa_compra)
        descuento_moneda = convertir_desde_clp(descuento, moneda_compra, tasa_compra)
        referencia = f"TRF-{random.randint(100000, 999999)}"

        if session.get('usuario_logueado'):
            items = construir_items_comprados(productos, carrito)
            api_post('/api/compras', {
                'usuario': session.get('usuario_nombre', ''),
                'buy_order': referencia,
                'metodo_pago': 'Transferencia',
                'estado_pago': 'En Espera',
                'estado_pedido': 'Pendiente',
                'metodo_entrega': metodo_entrega,
                'direccion_entrega': direccion_entrega,
                'moneda': moneda_compra,
                'tasa_cambio': tasa_compra,
                'subtotal': int(subtotal),
                'descuento': int(descuento),
                'total': int(total),
                'items': items,
            })

        return render_template(
            'transferencia.html',
            datos=DATOS_TRANSFERENCIA,
            referencia=referencia,
            moneda=moneda_compra,
            subtotal=subtotal_moneda,
            descuento=descuento_moneda,
            total=total_moneda,
            total_clp=total,
            metodo_entrega=metodo_entrega,
            direccion_entrega=direccion_entrega,
        )

    buy_order = str(random.randint(100000, 999999))
    return_url = url_for('confirmar_pago', _external=True)

    try:
        transaction = crear_transaccion()
        response = transaction.create(buy_order, buy_order, total, return_url)
        session['tbk_token'] = response['token']
        session['buy_order'] = buy_order
        session['moneda_compra'] = moneda_compra
        session['tasa_compra'] = tasa_compra
        return redirect(response['url'] + '?token_ws=' + response['token'])
    except Exception as e:
        flash(f"Ocurrió un error iniciando el pago: {str(e)}", "danger")
        return redirect(url_for('ver_carrito'))


@app.route('/confirmar_pago')
def confirmar_pago():
    token_ws = request.args.get('token_ws')

    if not token_ws:
        flash("Token de pago no recibido", "danger")
        return redirect(url_for('ver_carrito'))

    try:
        transaction = crear_transaccion()
        response = transaction.commit(token_ws)

        if response['status'] == 'AUTHORIZED':
            carrito = session.get('carrito', {})
            productos, subtotal, descuento, total = calcular_resumen_carrito(carrito)
            moneda_compra = session.get('moneda_compra', 'CLP')
            tasa_compra = float(session.get('tasa_compra', 1.0))
            metodo_entrega = session.get('metodo_entrega', 'Retiro en Tienda')
            direccion_entrega = session.get('direccion_entrega', '')
            estado_pago = 'Aprobado'

            items_comprados = construir_items_comprados(productos, carrito)

            # Descontar stock via backend
            api_post('/api/stock/descontar', {'items': items_comprados})

            # Registrar compra via backend
            if session.get('usuario_logueado') and items_comprados:
                api_post('/api/compras', {
                    'usuario': session.get('usuario_nombre', ''),
                    'buy_order': response.get('buy_order') or session.get('buy_order', 'SIN-ORDEN'),
                    'metodo_pago': 'Tarjeta',
                    'estado_pago': estado_pago,
                    'estado_pedido': 'Pendiente',
                    'metodo_entrega': metodo_entrega,
                    'direccion_entrega': direccion_entrega,
                    'moneda': moneda_compra,
                    'tasa_cambio': tasa_compra,
                    'subtotal': int(subtotal),
                    'descuento': int(descuento),
                    'total': int(total),
                    'items': items_comprados,
                })

            session.pop('carrito', None)
            session.pop('codigo_descuento_aplicado', None)
            session.pop('buy_order', None)
            session.pop('moneda_compra', None)
            session.pop('tasa_compra', None)
            session.pop('metodo_entrega', None)
            session.pop('direccion_entrega', None)

            return render_template("confirmacion.html", detalle=response,
                                   metodo_entrega=metodo_entrega, direccion_entrega=direccion_entrega)

        else:
            if session.get('usuario_logueado'):
                carrito = session.get('carrito', {})
                productos, subtotal, descuento, total = calcular_resumen_carrito(carrito)
                moneda_compra = session.get('moneda_compra', 'CLP')
                tasa_compra = float(session.get('tasa_compra', 1.0))
                items_comprados = construir_items_comprados(productos, carrito)

                if items_comprados:
                    api_post('/api/compras', {
                        'usuario': session.get('usuario_nombre', ''),
                        'buy_order': response.get('buy_order') or session.get('buy_order', 'SIN-ORDEN'),
                        'metodo_pago': 'Tarjeta',
                        'estado_pago': 'Rechazado',
                        'moneda': moneda_compra,
                        'tasa_cambio': tasa_compra,
                        'subtotal': int(subtotal),
                        'descuento': int(descuento),
                        'total': int(total),
                        'items': items_comprados,
                    })

            session.pop('buy_order', None)
            session.pop('moneda_compra', None)
            session.pop('tasa_compra', None)
            flash("El pago no fue autorizado", "danger")
            return redirect(url_for('ver_carrito'))

    except Exception as e:
        flash(f"Error al confirmar el pago: {str(e)}", "danger")
        return redirect(url_for('ver_carrito'))


# ─── Admin Stock ─────────────────────────────────────────────────────────────

@app.route('/admin/stock', methods=['GET', 'POST'])
def administrar_stock():
    if request.method == 'POST':
        updates = []
        for key, value in request.form.items():
            if key.startswith('stock_'):
                try:
                    producto_id = int(key.replace('stock_', ''))
                    updates.append({'id': producto_id, 'stock': value})
                except ValueError:
                    pass

        datos, error = api_post('/api/admin/stock', {'updates': updates})
        if error:
            flash(f"Error al actualizar stock: {error}", "danger")
        else:
            for err in (datos or {}).get('errores', []):
                flash(err, "danger")
            if not error and not (datos or {}).get('errores'):
                flash("Stock actualizado correctamente", "success")
        return redirect(url_for('administrar_stock'))

    datos, error = api_get('/api/admin/productos')
    if error:
        flash(f"No se pudo cargar el stock: {error}", "warning")
    productos = datos if datos else []
    return render_template('admin_stock.html', productos=productos)


# ─── Helper de autorización por rol ─────────────────────────────────────────
def _requiere_rol(*roles):
    if not session.get('usuario_logueado'):
        flash('Debes iniciar sesion para acceder a esta sección.', 'warning')
        return redirect(url_for('ver_carrito'))
    if session.get('usuario_rol') not in roles:
        flash('No tienes permisos para acceder a esta sección.', 'danger')
        return redirect(url_for('ver_carrito'))
    return None


# ════════════════════════════════════════════════════════════════════════════
#  DASHBOARD ADMINISTRADOR
# ════════════════════════════════════════════════════════════════════════════

@app.route('/admin')
def dashboard_admin():
    redir = _requiere_rol('admin')
    if redir:
        return redir

    from datetime import date
    mes = request.args.get('mes', type=int, default=date.today().month)
    anio = request.args.get('anio', type=int, default=date.today().year)

    reporte, err_rep = api_get('/api/reportes/ventas', params={'mes': mes, 'anio': anio})
    usuarios, err_usr = api_get('/api/usuarios')

    return render_template(
        'admin_dashboard.html',
        reporte=reporte or {},
        usuarios=usuarios or [],
        mes=mes,
        anio=anio,
        error_reporte=err_rep,
        error_usuarios=err_usr,
    )


@app.route('/admin/usuarios/<int:uid>/rol', methods=['POST'])
def admin_cambiar_rol(uid):
    redir = _requiere_rol('admin')
    if redir:
        return redir
    nuevo_rol = request.form.get('rol', '').strip()
    datos, error = api_put(f'/api/usuarios/{uid}/rol', {'rol': nuevo_rol})
    if error:
        flash(f'Error al cambiar rol: {error}', 'danger')
    elif not (datos or {}).get('ok'):
        flash((datos or {}).get('error', 'Error desconocido'), 'danger')
    else:
        flash(f'Rol actualizado correctamente a "{nuevo_rol}".', 'success')
    return redirect(url_for('dashboard_admin'))


# ════════════════════════════════════════════════════════════════════════════
#  DASHBOARD VENDEDOR
# ════════════════════════════════════════════════════════════════════════════

@app.route('/vendedor')
def dashboard_vendedor():
    redir = _requiere_rol('vendedor', 'admin')
    if redir:
        return redir

    pendientes, _ = api_get('/api/pedidos', params={'estado_pedido': 'Pendiente'})
    todos, _ = api_get('/api/pedidos')

    for lista in [pendientes or [], todos or []]:
        for p in lista:
            try:
                p['fecha'] = datetime.fromisoformat(p['fecha'])
            except (ValueError, TypeError):
                p['fecha'] = datetime.utcnow()

    return render_template(
        'vendedor_dashboard.html',
        pedidos_pendientes=pendientes or [],
        todos_pedidos=todos or [],
    )


@app.route('/vendedor/pedido/<int:pedido_id>/aprobar', methods=['POST'])
def vendedor_aprobar(pedido_id):
    redir = _requiere_rol('vendedor', 'admin')
    if redir:
        return redir
    datos, error = api_put(f'/api/pedidos/{pedido_id}/aprobar', {})
    if error:
        flash(f'Error: {error}', 'danger')
    elif not (datos or {}).get('ok'):
        flash((datos or {}).get('error', 'Error desconocido'), 'danger')
    else:
        flash('Pedido aprobado. Se notificó al bodeguero.', 'success')
    return redirect(url_for('dashboard_vendedor'))


@app.route('/vendedor/pedido/<int:pedido_id>/rechazar', methods=['POST'])
def vendedor_rechazar(pedido_id):
    redir = _requiere_rol('vendedor', 'admin')
    if redir:
        return redir
    datos, error = api_put(f'/api/pedidos/{pedido_id}/rechazar', {})
    if error:
        flash(f'Error: {error}', 'danger')
    elif not (datos or {}).get('ok'):
        flash((datos or {}).get('error', 'Error desconocido'), 'danger')
    else:
        flash('Pedido rechazado.', 'warning')
    return redirect(url_for('dashboard_vendedor'))


# ════════════════════════════════════════════════════════════════════════════
#  DASHBOARD BODEGUERO
# ════════════════════════════════════════════════════════════════════════════

@app.route('/bodeguero')
def dashboard_bodeguero():
    redir = _requiere_rol('bodeguero', 'admin')
    if redir:
        return redir

    aprobados, _ = api_get('/api/pedidos', params={'estado_pedido': 'Aprobado'})
    en_prep, _ = api_get('/api/pedidos', params={'estado_pedido': 'En Preparacion'})

    for lista in [aprobados or [], en_prep or []]:
        for p in lista:
            try:
                p['fecha'] = datetime.fromisoformat(p['fecha'])
            except (ValueError, TypeError):
                p['fecha'] = datetime.utcnow()

    return render_template(
        'bodeguero_dashboard.html',
        pedidos_aprobados=aprobados or [],
        pedidos_en_prep=en_prep or [],
    )


@app.route('/bodeguero/pedido/<int:pedido_id>/preparar', methods=['POST'])
def bodeguero_preparar(pedido_id):
    redir = _requiere_rol('bodeguero', 'admin')
    if redir:
        return redir
    datos, error = api_put(f'/api/pedidos/{pedido_id}/preparar', {})
    if error:
        flash(f'Error: {error}', 'danger')
    elif not (datos or {}).get('ok'):
        flash((datos or {}).get('error', 'Error desconocido'), 'danger')
    else:
        flash('Pedido marcado como En Preparación.', 'success')
    return redirect(url_for('dashboard_bodeguero'))


@app.route('/bodeguero/pedido/<int:pedido_id>/listo', methods=['POST'])
def bodeguero_listo(pedido_id):
    redir = _requiere_rol('bodeguero', 'admin')
    if redir:
        return redir
    datos, error = api_put(f'/api/pedidos/{pedido_id}/listo', {})
    if error:
        flash(f'Error: {error}', 'danger')
    elif not (datos or {}).get('ok'):
        flash((datos or {}).get('error', 'Error desconocido'), 'danger')
    else:
        flash('Pedido marcado como Listo para Entrega.', 'success')
    return redirect(url_for('dashboard_bodeguero'))


# ════════════════════════════════════════════════════════════════════════════
#  DASHBOARD CONTADOR
# ════════════════════════════════════════════════════════════════════════════

@app.route('/contador')
def dashboard_contador():
    redir = _requiere_rol('contador', 'admin')
    if redir:
        return redir

    transferencias, _ = api_get('/api/pedidos', params={'estado_pago': 'En Espera'})
    listos, _ = api_get('/api/pedidos', params={'estado_pedido': 'Listo para Entrega'})

    for lista in [transferencias or [], listos or []]:
        for p in lista:
            try:
                p['fecha'] = datetime.fromisoformat(p['fecha'])
            except (ValueError, TypeError):
                p['fecha'] = datetime.utcnow()

    return render_template(
        'contador_dashboard.html',
        transferencias_pendientes=transferencias or [],
        pedidos_listos=listos or [],
    )


@app.route('/contador/pedido/<int:pedido_id>/confirmar_pago', methods=['POST'])
def contador_confirmar_pago(pedido_id):
    redir = _requiere_rol('contador', 'admin')
    if redir:
        return redir
    datos, error = api_put(f'/api/pedidos/{pedido_id}/confirmar_pago', {})
    if error:
        flash(f'Error: {error}', 'danger')
    elif not (datos or {}).get('ok'):
        flash((datos or {}).get('error', 'Error desconocido'), 'danger')
    else:
        flash('Pago por transferencia confirmado correctamente.', 'success')
    return redirect(url_for('dashboard_contador'))


@app.route('/contador/pedido/<int:pedido_id>/entregar', methods=['POST'])
def contador_entregar(pedido_id):
    redir = _requiere_rol('contador', 'admin')
    if redir:
        return redir
    datos, error = api_put(f'/api/pedidos/{pedido_id}/entregar', {})
    if error:
        flash(f'Error: {error}', 'danger')
    elif not (datos or {}).get('ok'):
        flash((datos or {}).get('error', 'Error desconocido'), 'danger')
    else:
        flash('Entrega del producto registrada correctamente.', 'success')
    return redirect(url_for('dashboard_contador'))


if __name__ == '__main__':
    app.run(port=5000, debug=True)
