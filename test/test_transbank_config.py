from unittest.mock import patch

import transbank_config


@patch('transbank_config.Transaction')
@patch('transbank_config.WebpayOptions')
def test_crear_transaccion_devuelve_transaction(mock_webpay_options, mock_transaction):
    mock_options = mock_webpay_options.return_value

    resultado = transbank_config.crear_transaccion()

    mock_webpay_options.assert_called_once()
    mock_transaction.assert_called_once_with(mock_options)
    assert resultado == mock_transaction.return_value
