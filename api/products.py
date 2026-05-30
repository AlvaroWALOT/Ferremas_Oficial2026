from flask import Blueprint, jsonify
from models import Producto, Precio
from datetime import datetime

products_api = Blueprint('products_api', __name__)

@products_api.route('/', methods=['GET'])
def get_products():
    productos = Producto.query.all()
    resultado = []
    for p in productos:
        precios = []
        for precio in p.precios:
            precios.append({
                "Fecha": precio.fecha.isoformat(),
                "Valor": precio.valor
            })
        resultado.append({
            "Código del producto": p.codigo_producto,
            "Marca": p.marca,
            "Código": p.codigo_interno,
            "Nombre": p.nombre,
            "Precio": precios,
            "Stock": p.stock
        })
    return jsonify(resultado)
