import os
import re
import json
import time
import pprint
import logging
from dotenv import load_dotenv
from telebot import TeleBot, types
from aliexpress_api import AliexpressApi, models
from urllib.parse import urlparse, parse_qs, urlencode
from http.server import BaseHTTPRequestHandler, HTTPServer

load_dotenv()

TOKEN = os.getenv('TOKEN_BOT')
if not TOKEN:
    print("[ERRO] TOKEN_BOT não encontrado nas variáveis de ambiente.")
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
    print("[OK] API do AliExpress configurada com sucesso.")
except Exception as e:
    print(f"[ERRO] Falha ao configurar API do AliExpress: {e}")
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
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        update = json.loads(post_data.decode('utf-8'))

        try:
            if 'message' in update or 'callback_query' in update:
                bot.process_new_updates([types.Update.de_json(update)])
                print("[OK] Update processado com sucesso.")
        except Exception as e:
            logging.error(f"Erro ao processar update: {e}")

        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()
        self.wfile.write("Bot está rodando.".encode('utf-8'))

def obter_links_afiliados(mensagem, id_mensagem, link_produto):
    try:
        codigo_rastreamento = os.getenv('ID_RASTREAMENTO')
        links_afiliados = api_aliexpress.get_affiliate_links(f'{link_produto}?utm_source={codigo_rastreamento}&sourceType=620&improveDiscount=Y&BuyNow=true')
        
        pprint.pp(links_afiliados)
        link_afiliado = link_super = link_limitado = links_afiliados[0].promotion_link

        timestamp = str(int(float("%.2f" % (float(time.time()))) * 1000))
        detalhes_produto = api_aliexpress.get_products_details([timestamp,f'https://star.aliexpress.com/share/share.htm?platform=AE&businessType=ProductDetail&redirectUrl={link_produto}'])
        
        pprint.pp(detalhes_produto)
        titulo_produto = detalhes_produto[0].product_title
        preco_produto = detalhes_produto[0].target_sale_price
        imagem_produto = detalhes_produto[0].product_main_image_url
        
        bot.delete_message(mensagem.chat.id, id_mensagem)
        
        bot.send_photo(
            mensagem.chat.id,
            imagem_produto,
            caption=(
                "🛒 Seu produto é:\n\n"
                f"{titulo_produto}\n\n"
                f"💵 *Preço do produto:* R$ {float(preco_produto):,.2f}\n\n"
                f"🔗 *Link do produto:* {link_afiliado}\n\n"
                f"Compare preços e compre \n\n"
                f"💰 Exibição de moeda (preço final na finalização da compra): \n\n"
                f"Link {link_afiliado} \n\n"
                f"💎 Super oferta: \n\n"
                f"Link {link_super} \n\n"
                f"♨️ Oferta limitada: \n\n"
                f"Link {link_limitado} \n\n"
                "#PromocaoAliXpress:✅"
            ),
            reply_markup=menu_padrao
        )
    except Exception as e:
        bot.send_message(
            mensagem.chat.id, 
            "Algo deu errado \n " + str(e)
        )

def extrair_url_do_texto(texto):
    padrao_url = r'https?://\S+|www\.\S+'
    urls = re.findall(padrao_url, texto)
    return urls[0] if urls else None

def construir_link_carrinho(link_original):
    parametros = extrair_parametros_url(link_original)
    url_base_carrinho = "https://www.aliexpress.com/p/trade/confirm.html?"
    parametros_carrinho = {
        "availableProductShopcartIds": ",".join(parametros.get("availableProductShopcartIds", [])),
        "extraParams": json.dumps(
            {"channelInfo": {"sourceType": "620"}}, 
            separators=(',', ':')
        )
    }
    return criar_url_com_parametros(url_base_carrinho, parametros_carrinho)

def extrair_parametros_url(url):
    url_analisada = urlparse(url)
    return parse_qs(url_analisada.query)

def criar_url_com_parametros(url_base, parametros):
    return url_base + urlencode(parametros)

def obter_link_desconto_carrinho(link_carrinho, mensagem):
    try:
        link_carrinho_formatado = construir_link_carrinho(link_carrinho)
        link_afiliado = api_aliexpress.get_affiliate_links(link_carrinho_formatado)[0].promotion_link

        mensagem_desconto = (
            f"Este é o link para o desconto no carrinho. \n"
            f"{str(link_afiliado)}"
        )

        caminho_imagem = "assets/bibi-1.jpg"
        with open(caminho_imagem, "rb") as img:
            bot.send_photo(mensagem.chat.id, img, caption=mensagem_desconto)
    except Exception as e:
        bot.send_message(mensagem.chat.id, f"Algo deu errado \n{e}")

def registrar_handlers():
    """
    Registra todos os handlers do bot:
    - Mensagens de texto
    - Comandos (/start, etc)
    - Callback queries (botões)
    """
    
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
                "👥 Ver lista de usuários ativos\n\n"
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
                parse_mode="Markdown"
            )

    @bot.message_handler(func=lambda m: True)
    def handle_mensagem(mensagem):
        try:
            url_produto = extrair_url_do_texto(mensagem.text)
            mensagem_carregando = bot.send_message(
                mensagem.chat.id,
                "⏳ Aguarde um momento, as ofertas estão sendo preparadas..."
            )

            if url_produto and "aliexpress.com" in url_produto:
                if "p/shoppingcart" in mensagem.text.lower():
                    return

                if "availableProductShopcartIds" in mensagem.text.lower():
                    obter_link_desconto_carrinho(url_produto, mensagem)
                    return

                obter_links_afiliados(mensagem, mensagem_carregando.message_id, url_produto)
            else:
                bot.delete_message(mensagem.chat.id, mensagem_carregando.message_id)
                bot.send_message(
                    mensagem.chat.id,
                    "❌ O link é inválido!\nVerifique o link do produto.",
                    parse_mode='HTML'
                )
        except Exception as e:
            print(f"[ERRO] Falha ao processar mensagem: {e}")
            bot.send_message(
                mensagem.chat.id,
                "⚠️ Erro interno ao processar sua mensagem. Tente novamente."
            )
    
    print("[OK] Handler para mensagens registrado.")

def start_server():
    PORT = int(os.getenv('PORT', 8080))
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, WebhookHandler)
    print(f"[OK] Servidor HTTP iniciado na porta {PORT}.")
    httpd.serve_forever()

def configurar_webhook():
    url_webhook = os.getenv('URL_WEBHOOK')
    if not url_webhook:
        print("[ERRO] WEBHOOK_URL não configurado nas variáveis de ambiente.")
        return False
    try:
        bot.remove_webhook()
        time.sleep(1)
        sucesso = bot.set_webhook(url_webhook)
        if sucesso:
            print(f"[OK] Webhook configurado: {url_webhook}")
            return True
        else:
            print("[ERRO] Falha ao configurar webhook.")
            return False
    except Exception as e:
        print(f"[ERRO] Exceção ao configurar webhook: {e}")
        return False

if __name__ == "__main__":
    print("[INFO] Inicializando bot...")

    registrar_handlers()

    if configurar_webhook():
        start_server()
    else:
        print("[ERRO] Bot não iniciou devido a problema no webhook.")