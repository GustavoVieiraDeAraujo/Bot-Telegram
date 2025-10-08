import os
import re
import sys
import json
import time
import logging
import requests
from dotenv import load_dotenv
from telebot import TeleBot, types
from aliexpress_api import AliexpressApi, models
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs, unquote

# -------------------------------------------------------
# Configuração de logging
# -------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s]: %(message)s"
)

# -------------------------------------------------------
# Carrega variáveis de ambiente
# -------------------------------------------------------
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ALIEXPRESS_APP_KEY = os.getenv("ALIEXPRESS_APP_KEY")
ALIEXPRESS_APP_SECRET = os.getenv("ALIEXPRESS_APP_SECRET")
PORT = int(os.getenv("PORT", 8080))

if not TELEGRAM_TOKEN or not ALIEXPRESS_APP_KEY or not ALIEXPRESS_APP_SECRET:
    logging.error("❌ Erro: variáveis de ambiente ausentes (TELEGRAM_TOKEN, ALIEXPRESS_APP_KEY, ALIEXPRESS_APP_SECRET)")
    sys.exit(1)

bot = TeleBot(TELEGRAM_TOKEN)
api_aliexpress = AliexpressApi(ALIEXPRESS_APP_KEY, ALIEXPRESS_APP_SECRET)

# -------------------------------------------------------
# Função para normalizar links do AliExpress
# -------------------------------------------------------
def normalize_aliexpress_url(url):
    """
    Extrai o ID do produto da URL e retorna a URL canônica:
    https://www.aliexpress.com/item/<ID>.html

    Suporta:
    - /item/ID.html
    - productId, objectId, productIds no query
    - links SSR (/ssr/...)
    - links 'share' e 'redirect'
    """
    try:
        if not url:
            return url

        # Caso 1: padrão clássico /item/123.html
        m = re.search(r"/item/(\d+)\.html", url)
        if m:
            product_id = m.group(1)
            return f"https://www.aliexpress.com/item/{product_id}.html"

        # Caso 2: productIds, productId, objectId, etc.
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        for key in ("productIds", "productId", "objectId", "product_id"):
            if key in qs and qs[key]:
                product_id = re.search(r"(\d+)", qs[key][0])
                if product_id:
                    product_id = product_id.group(1)
                    return f"https://www.aliexpress.com/item/{product_id}.html"

        # Caso 3: /ssr/xxxxx/... com productIds embutido na URL
        if "/ssr/" in url:
            m = re.search(r"productIds=(\d+)", url)
            if m:
                product_id = m.group(1)
                return f"https://www.aliexpress.com/item/{product_id}.html"

        # Caso 4: links curtos (a.aliexpress.com ou s.click.aliexpress.com)
        if "a.aliexpress.com" in url or "s.click.aliexpress.com" in url:
            r = requests.get(url, allow_redirects=True, timeout=10)
            if r.url and "aliexpress.com/item/" in r.url:
                return normalize_aliexpress_url(r.url)

        # Fallback
        return url

    except Exception as e:
        logging.warning(f"[WARN] normalize_aliexpress_url falhou: {e}")
        return url

# -------------------------------------------------------
# Função para gerar link de afiliado
# -------------------------------------------------------
def gerar_link_afiliado(link_original):
    try:
        logging.info(f"🔗 Gerando link afiliado para: {link_original}")
        link_normalizado = normalize_aliexpress_url(link_original)

        res = api_aliexpress.get_affiliate_links(link_normalizado)
        if not res or "resp_result" not in res:
            return None

        result_data = json.loads(res["resp_result"])
        affiliate_link = result_data.get("result", {}).get("promotion_link", None)

        if affiliate_link:
            return affiliate_link
        else:
            logging.error(f"❌ Nenhum link afiliado retornado para {link_original}")
            return None

    except Exception as e:
        logging.error(f"❌ Erro ao gerar link afiliado: {e}")
        return None

# -------------------------------------------------------
# Handler principal do bot
# -------------------------------------------------------
@bot.message_handler(commands=["start", "help"])
def enviar_boas_vindas(msg):
    texto = (
        "👋 Olá! Envie um link do AliExpress e eu gerarei seu link de afiliado.\n\n"
        "Exemplo:\n"
        "https://pt.aliexpress.com/item/1005008441505437.html\n\n"
        "Também aceito links curtos e SSR!"
    )
    bot.reply_to(msg, texto)

# -------------------------------------------------------
# Processa mensagens com links
# -------------------------------------------------------
@bot.message_handler(func=lambda msg: True)
def processar_mensagem(msg):
    texto = msg.text.strip()
    match = re.search(r"(https?://[^\s]+)", texto)

    if not match:
        bot.reply_to(msg, "⚠️ Envie um link válido do AliExpress.")
        return

    url = match.group(1)
    bot.reply_to(msg, "⏳ Gerando seu link de afiliado... aguarde...")

    link_afiliado = gerar_link_afiliado(url)

    if link_afiliado:
        bot.reply_to(msg, f"✅ Aqui está seu link de afiliado:\n\n{link_afiliado}")
    else:
        bot.reply_to(msg, "❌ Algo deu errado.\nO link pode ser inválido ou o produto não é elegível para afiliados.")

# -------------------------------------------------------
# Servidor HTTP para manter o bot ativo (usado no deploy)
# -------------------------------------------------------
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write("<h3>🤖 Bot AliExpress ativo.</h3>".encode("utf-8"))

def iniciar_http_server():
    server = HTTPServer(("0.0.0.0", PORT), KeepAliveHandler)
    logging.info(f"🌐 Servidor HTTP rodando na porta {PORT}")
    server.serve_forever()

# -------------------------------------------------------
# Execução principal
# -------------------------------------------------------
if __name__ == "__main__":
    from threading import Thread

    # Thread paralela para HTTP server
    Thread(target=iniciar_http_server, daemon=True).start()

    logging.info("🚀 Bot iniciado. Aguardando mensagens...")
    bot.infinity_polling(timeout=60, long_polling_timeout=30)
