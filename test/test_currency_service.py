from unittest.mock import patch

from services.currency import obtener_tipo_cambio


@patch('services.currency.requests.get')
def test_obtener_tipo_cambio_usd(mock_get):
    mock_get.return_value.json.return_value = {'serie': [{'valor': 850.5}]}

    tasa = obtener_tipo_cambio('USD')

    assert tasa == 850.5
    mock_get.assert_called_once_with('https://mindicador.cl/api/dolar')


@patch('services.currency.requests.get')
def test_obtener_tipo_cambio_eur(mock_get):
    mock_get.return_value.json.return_value = {'serie': [{'valor': 920.0}]}

    tasa = obtener_tipo_cambio('EUR')

    assert tasa == 920.0
    mock_get.assert_called_once_with('https://mindicador.cl/api/euro')


@patch('services.currency.requests.get')
def test_obtener_tipo_cambio_error_network(mock_get):
    mock_get.side_effect = Exception('error de red')

    tasa = obtener_tipo_cambio('USD')

    assert tasa == 1


def test_obtener_tipo_cambio_desconocido():
    tasa = obtener_tipo_cambio('XYZ')

    assert tasa == 1
