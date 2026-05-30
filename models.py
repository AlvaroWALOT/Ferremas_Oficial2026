from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), nullable=False, default='cliente')
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo_producto = db.Column(db.String(20), unique=True, nullable=False)
    marca = db.Column(db.String(50))
    codigo_interno = db.Column(db.String(20), unique=True)
    nombre = db.Column(db.String(100), nullable=False)
    stock = db.Column(db.Integer, default=0)
    imagen_url = db.Column(db.String(255))  # URL de la imagen del producto
    categoria = db.Column(db.String(50))  # o relación a tabla Categoria
    destacado = db.Column(db.Boolean, default=False)  # ⬅️ Agregado aquí
    
    

class Precio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    fecha = db.Column(db.DateTime, nullable=False)
    valor = db.Column(db.Float, nullable=False)
    producto = db.relationship('Producto', backref='precios')


class CompraHistorial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(50), nullable=False, index=True)
    buy_order = db.Column(db.String(50), nullable=False)
    metodo_pago = db.Column(db.String(20), nullable=False, default='Tarjeta')
    estado_pago = db.Column(db.String(30), nullable=False, default='En Espera')
    estado_pedido = db.Column(db.String(30), nullable=False, default='Pendiente')
    metodo_entrega = db.Column(db.String(30), nullable=False, default='Retiro en Tienda')
    direccion_entrega = db.Column(db.String(255))
    moneda = db.Column(db.String(10), nullable=False, default='CLP')
    tasa_cambio = db.Column(db.Float, nullable=False, default=1.0)
    subtotal = db.Column(db.Integer, nullable=False, default=0)
    descuento = db.Column(db.Integer, nullable=False, default=0)
    total = db.Column(db.Integer, nullable=False, default=0)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    detalle_items = db.Column(db.Text, nullable=False)
