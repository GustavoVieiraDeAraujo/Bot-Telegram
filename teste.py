import os
from dotenv import load_dotenv
from aliexpress_api import AliexpressApi, models

load_dotenv()

api_aliexpress = AliexpressApi(
    os.getenv("CHAVE_APP"),
    os.getenv("SEGREDO_APP"),
    models.Language.PT,
    models.Currency.BRL,
    os.getenv("ID_RASTREAMENTO"),
)

response_afiliados = api_aliexpress.get_affiliate_links('https://s.click.aliexpress.com/e/_ooj4Ejw')

print(response_afiliados)