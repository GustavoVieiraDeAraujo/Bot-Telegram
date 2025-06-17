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
from urllib.parse import urlparse, parse_qs, urlencode, unquote

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    stream=sys.stdout
)

load_dotenv()

TOKEN = os.getenv('TOKEN_BOT')
if not TOKEN:
    logging.error("[ERRO] TOKEN_BOT não encontrado nas variáveis de ambiente.")
    exit(1)
bot = TeleBot(TOKEN, threaded=False)

try:
    api_aliexpress = AliexpressApi(
        os.getenv('CHAVE_APP'),
        os.getenv('SEGREDO_APP'),
        models.Language.PT,
        models.Currency.BRL,
        os.getenv('ID_RASTREAMENTO')
    )
    logging.info("[OK] API do AliExpress configurada com sucesso.")
except Exception as e:
    logging.error(f"[ERRO] Falha ao configurar API do AliExpress: {e}")
    exit(1)

menu_padrao = types.InlineKeyboardMarkup(row_width=1)
botao_chat = types.InlineKeyboardButton("💬 Chat 💬", url=os.getenv('LINK_TELEGRAM_CHAT'))
botao_promocoes = types.InlineKeyboardButton("🔥 Promoções 🔥", url=os.getenv('LINK_TELEGRAM_OFERTAS'))
botao_youtube = types.InlineKeyboardButton("🎥 Youtube 🎥", url=os.getenv('LINK_YOUTUBE'))
menu_padrao.add(botao_chat, botao_promocoes, botao_youtube)

menu_admin = types.InlineKeyboardMarkup(row_width=1)
um = types.InlineKeyboardButton("1", url="https://s.click.aliexpress.com/e/_ol8VJ2T")
dois = types.InlineKeyboardButton("2", url="https://s.click.aliexpress.com/e/_DlCyg5Z")
tres = types.InlineKeyboardButton("3", url="https://s.click.aliexpress.com/e/_DBBkt9V")
quatro = types.InlineKeyboardButton("4", url="https://s.click.aliexpress.com/e/_DdcXZ2r")
cinco = types.InlineKeyboardButton("5", url="https://s.click.aliexpress.com/e/_DDs7W5D")
menu_admin.add(um, dois, tres, quatro, cinco, botao_chat, botao_promocoes, botao_youtube)

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        update = json.loads(post_data.decode('utf-8'))

        try:
            if 'message' in update or 'callback_query' in update:
                bot.process_new_updates([types.Update.de_json(update)])
                logging.info("[OK] Update processado com sucesso.")
        except Exception as e:
            logging.error(f"Erro ao processar update: {e}")

        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b'OK')

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type','text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write("Bot está rodando.".encode('utf-8'))

def obter_links_afiliados(mensagem, id_mensagem, link_produto):
    try:
        codigo_rastreamento = os.getenv('ID_RASTREAMENTO')

        link_promocao = construir_link_promocao(link_produto)
        logging.info(f"Link Promocao: {link_promocao}")

        link_carrinho_com_rastreamento = (
            f'{link_promocao}?utm_source={codigo_rastreamento}'
        )
        logging.info(f"Link Carrinho com Rastreamento: {link_carrinho_com_rastreamento}")

        links_afiliados = api_aliexpress.get_affiliate_links(link_carrinho_com_rastreamento)
        link_afiliado_carrinho = links_afiliados[0].promotion_link
        logging.info(f"Link Afiliado Carrinho: {link_afiliado_carrinho}")

        timestamp = str(int(float("%.2f" % (float(time.time()))) * 1000))
        detalhes_produto = api_aliexpress.get_products_details([
            timestamp,
            f'https://star.aliexpress.com/share/share.htm?platform=AE&businessType=ProductDetail&redirectUrl={link_produto}'
        ])

        titulo_produto = detalhes_produto[0].product_title
        preco_produto = detalhes_produto[0].target_sale_price
        imagem_produto = detalhes_produto[0].product_main_image_url

        bot.delete_message(mensagem.chat.id, id_mensagem)

        bot.send_photo(
            mensagem.chat.id,
            imagem_produto,
            caption=(
                "🛒 Seu carrinho com desconto está pronto:\n\n"
                f"{titulo_produto}\n\n"
                f"💵 Preço do produto: R$ {float(preco_produto):,.2f}\n\n"
                f"🔗 Finalize sua compra:\n{link_afiliado_carrinho}\n\n"
                "#PromocaoAliExpress ✅"
            ),
            reply_markup=menu_padrao,
            reply_to_message_id=mensagem.message_id
        )
    except Exception as e:
        bot.send_message(
            mensagem.chat.id, 
            "Algo deu errado \n " + str(e),
            reply_to_message_id=mensagem.message_id
        )

def extrair_url_do_texto(texto):
    padrao_url = r'https?://\S+|www\.\S+'
    urls = re.findall(padrao_url, texto)
    return urls[0] if urls else None

def construir_link_promocao(link_original):
    parametros = extrair_parametros_url(link_original)
    logging.info(f"Parâmetros extraídos: {parametros}")

    object_id = parametros.get("product_id", [None])[0]
    logging.info(f"ID do objeto: {object_id}")

    if not object_id:
        m = re.search(r'/item/(\d+).html', link_original)
        if m:
            object_id = m.group(1)

    if not object_id:
        return None

    url_promocao = (
        "https://m.aliexpress.com/p/coin-index/index.html"
        "?_immersiveMode=true"
        f"&productIds={object_id}"
    )

    logging.info(f"URL de promoção: {url_promocao}")
    return url_promocao

def extrair_parametros_url(url):
    url_analisada = urlparse(url)
    return parse_qs(url_analisada.query)

def criar_url_com_parametros(url_base, parametros):
    return url_base + urlencode(parametros)

def obter_link_desconto_carrinho(link_carrinho, mensagem):
    try:
        link_carrinho_formatado = construir_link_promocao(link_carrinho)
        link_afiliado = api_aliexpress.get_affiliate_links(link_carrinho_formatado)[0].promotion_link

        mensagem_desconto = (
            f"Este é o link para o desconto no carrinho. \n"
            f"{str(link_afiliado)}"
        )

        caminho_imagem = "assets/bibi-1.jpg"
        with open(caminho_imagem, "rb") as img:
            bot.send_photo(mensagem.chat.id, img, caption=mensagem_desconto, reply_to_message_id=mensagem.message_id)
    except Exception as e:
        bot.send_message(mensagem.chat.id, f"Algo deu errado \n{e}", reply_to_message_id=mensagem.message_id)

def registrar_handlers():
    @bot.message_handler(commands=['start'])
    def handle_start(mensagem):
        user_id = mensagem.from_user.id
        nome_usuario = mensagem.from_user.first_name

        if user_id == 5206185262:
            menu = menu_admin
            mensagem_boas_vindas = (
                f"🔐 Olá Papai {nome_usuario}!\n\n"
                "Você está no menu Admin.\n\n"
                "Com este painel, você pode:\n\n"
                "🛠 Enviar notificações aos usuários\n"
                "📊 Ver estatísticas de uso\n"
                "📦 Gerenciar promoções e ofertas\n"
                "⚠️ Use as funcionalidades com responsabilidade!"
            )
        else:
            menu = menu_padrao
            mensagem_boas_vindas = (
                f"👋 Olá, {nome_usuario}! Seja bem-vindo ao bot de ofertas do AliExpress!\n\n"
                "Envie qualquer link do AliExpress para gerar:\n\n"
                "🤑 Bônus de Moedas | 🔥 Super Oferta | ⚡ Oferta Relâmpago\n\n"
                "📌 *Como usar:*\n\n"
                "1️⃣ Envie um link do AliExpress\n"
                "2️⃣ Escolha a promoção desejada\n"
                "3️⃣ Aproveite seus descontos!\n\n"
                "🔗 *Nossos canais:*"
            )

        with open('assets/bibi-2.jpg', 'rb') as foto:
            bot.send_photo(
                mensagem.chat.id,
                foto,
                caption=mensagem_boas_vindas,
                reply_markup=menu,
                parse_mode="Markdown",
                reply_to_message_id=mensagem.message_id
            )

    @bot.message_handler(func=lambda m: True)
    def handle_mensagem(mensagem):
        try:
            url_produto = extrair_url_do_texto(mensagem.text)
            mensagem_carregando = bot.send_message(
                mensagem.chat.id,
                "⏳ Aguarde um momento, a oferta está sendo preparada..."
            )

            if url_produto and "aliexpress.com" in url_produto:
                if "s.click.aliexpress.com" in url_produto:
                    url_produto = resolver_link_ali(url_produto)
                    
                if "availableProductShopcartIds" in url_produto:
                    obter_link_desconto_carrinho(url_produto, mensagem)
                else:
                    obter_links_afiliados(mensagem, mensagem_carregando.message_id, url_produto)
            else:
                bot.delete_message(mensagem.chat.id, mensagem_carregando.message_id)
                bot.send_message(
                    mensagem.chat.id,
                    "❌ O link é inválido!\nVerifique o link do produto.",
                    parse_mode='HTML',
                    reply_to_message_id=mensagem.message_id
                )
        except Exception as e:
            logging.error(f"[ERRO] Falha ao processar mensagem: {e}")
            bot.send_message(
                mensagem.chat.id,
                "⚠️ Ocorreu um erro ao processar sua mensagem.\nTente novamente.",
                reply_to_message_id=mensagem.message_id
            )

    logging.info("[OK] Handler para mensagens registrado.")

def start_server():
    PORT = int(os.getenv('PORT', 8080))
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, WebhookHandler)
    logging.info(f"[OK] Servidor HTTP iniciado na porta {PORT}.")
    httpd.serve_forever()

def configurar_webhook():
    url_webhook = os.getenv('URL_WEBHOOK')
    if not url_webhook:
        logging.error("[ERRO] WEBHOOK_URL não configurado nas variáveis de ambiente.")
        return False
    try:
        bot.remove_webhook()
        time.sleep(1)
        sucesso = bot.set_webhook(url_webhook)
        if sucesso:
            logging.info(f"[OK] Webhook configurado: {url_webhook}")
            return True
        else:
            logging.error("[ERRO] Falha ao configurar webhook.")
            return False
    except Exception as e:
        logging.error(f"[ERRO] Exceção ao configurar webhook: {e}")
        return False
    
def extrair_redirect_url_recursiva(url):
    while True:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        if 'redirectUrl' in query_params:
            redirect_url = unquote(query_params['redirectUrl'][0])
            if 'aliexpress.com/item/' in redirect_url:
                return redirect_url
            url = redirect_url
        else:
            return url

def resolver_link_ali(link_encurtado, max_redirects=5):
    url = link_encurtado
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0'}
    redirects = 0

    while redirects < max_redirects:
        response = session.head(url, allow_redirects=False, headers=headers)
        if 300 <= response.status_code < 400 and 'Location' in response.headers:
            url = response.headers['Location']
            redirects += 1
        else:
            break
    url_final = extrair_redirect_url_recursiva(url)
    return url_final

if __name__ == "__main__":
    logging.info("[INFO] Inicializando bot...")

    registrar_handlers()

    if configurar_webhook():
        start_server()
    else:
        logging.error("[ERRO] Bot não iniciou devido a problema no webhook.")