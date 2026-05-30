# currency.py
import requests

def obtener_tipo_cambio(moneda_origen='USD'):
    try:
        if moneda_origen == 'USD':
            url = 'https://mindicador.cl/api/dolar'
        elif moneda_origen == 'EUR':
            url = 'https://mindicador.cl/api/euro'
        elif moneda_origen == 'UF':
            url = 'https://mindicador.cl/api/uf'
        else:
            return 1  # CLP o desconocido: tasa = 1

        response = requests.get(url)
        data = response.json()
        tasa = float(data['serie'][0]['valor'])
        return tasa
    except Exception as e:
        print("Error al obtener tipo de cambio:", e)
        return 1  # valor por defecto
