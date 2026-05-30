from transbank.webpay.webpay_plus.transaction import Transaction, WebpayOptions
from transbank.common.integration_type import IntegrationType

def crear_transaccion():
    options = WebpayOptions(
        integration_type=IntegrationType.TEST,
        commerce_code="597055555532",
        api_key="579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C"
    )
    return Transaction(options)
 