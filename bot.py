import os
import sys
import json
import logging
from dotenv import load_dotenv
from telebot import TeleBot, types
from http.server import BaseHTTPRequestHandler, HTTPServer

import config
from providers import carregar_providers_ativos, encontrar_provider

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    stream=sys.stdout,
)

load_dotenv()

TOKEN = os.getenv("TOKEN_BOT")
if not TOKEN:
    logging.error("[ERRO] TOKEN_BOT não encontrado nas variáveis de ambiente.")
    exit(1)
bot = TeleBot(TOKEN, threaded=False)

PROVIDERS_ATIVOS = carregar_providers_ativos()
if not PROVIDERS_ATIVOS:
    logging.error("[ERRO] Nenhum provider de afiliados ativo. Configure as credenciais no .env (veja README).")
    exit(1)

ADMIN_USER_IDS = config.obter_admin_user_ids()

# ====================== MENUS ==========================
def construir_menu_padrao():
    menu = types.InlineKeyboardMarkup(row_width=1)
    botoes = []
    if os.getenv("LINK_TELEGRAM_CHAT"):
        botoes.append(types.InlineKeyboardButton("💬 Chat 💬", url=os.getenv("LINK_TELEGRAM_CHAT")))
    if os.getenv("LINK_TELEGRAM_OFERTAS"):
        botoes.append(types.InlineKeyboardButton("🔥 Promoções 🔥", url=os.getenv("LINK_TELEGRAM_OFERTAS")))
    if os.getenv("LINK_YOUTUBE"):
        botoes.append(types.InlineKeyboardButton("🎥 Youtube 🎥", url=os.getenv("LINK_YOUTUBE")))
    if botoes:
        menu.add(*botoes)
    return menu

def construir_menu_admin():
    menu = construir_menu_padrao()
    links_extras = config.obter_links_rapidos_admin()
    if links_extras:
        menu.add(*[types.InlineKeyboardButton(item["label"], url=item["url"]) for item in links_extras])
    return menu

menu_padrao = construir_menu_padrao()
menu_admin = construir_menu_admin()

# ====================== SERVIDOR WEBHOOK ==========================
class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        try:
            update = json.loads(post_data.decode("utf-8"))
            if isinstance(update, dict) and ("message" in update or "callback_query" in update):
                bot.process_new_updates([types.Update.de_json(update)])
                logging.info("[OK] Update processado com sucesso.")
        except json.JSONDecodeError as e:
            logging.warning(f"[WARN] Payload invalido recebido no webhook: {e}")
            self.send_response(400)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Invalid JSON")
            return
        except Exception as e:
            logging.error(f"[ERRO] Falha ao processar update: {e}")

        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"OK")

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("Bot está rodando.".encode("utf-8"))

# ====================== FUNÇÕES DE URL ==========================
def extrair_url_do_texto(texto):
    import re
    padrao_url = r"https?://\S+|www\.\S+"
    urls = re.findall(padrao_url, texto or "")
    return urls[0] if urls else None

# ====================== ENVIO DE RESPOSTAS ==========================
def enviar_links_afiliados(provider, mensagem, id_mensagem_carregando, url_produto):
    try:
        links = provider.get_affiliate_links(url_produto)
        titulo_produto, imagem_produto = provider.get_product_details(url_produto)

        try:
            bot.delete_message(mensagem.chat.id, id_mensagem_carregando)
        except Exception:
            pass

        partes = ["🛒 Seu produto com desconto está pronto:\n\n"]
        if titulo_produto:
            partes.append(f"{titulo_produto}\n\n")
        if links.get("promo"):
            partes.append(f"🔗 Link promocional:\n{links['promo']}\n\n")
        if links.get("direct"):
            partes.append(f"🔗 Link direto do produto:\n{links['direct']}\n\n")
        partes.append("👇 Confira também nossos canais 👇")
        legenda_final = "".join(partes)

        if imagem_produto:
            try:
                bot.send_photo(
                    mensagem.chat.id,
                    imagem_produto,
                    caption=legenda_final,
                    reply_markup=menu_padrao,
                    reply_to_message_id=mensagem.message_id,
                )
                return
            except Exception as e:
                logging.warning(f"[WARN] Falha ao enviar foto: {e} — enviando texto.")

        bot.send_message(
            mensagem.chat.id,
            legenda_final,
            reply_markup=menu_padrao,
            reply_to_message_id=mensagem.message_id,
        )
    except Exception as e:
        logging.error(f"[ERRO] Falha ao obter links afiliados: {e}")
        bot.send_message(
            mensagem.chat.id,
            "⚠️ Algo deu errado ao gerar seus links. Tente novamente em instantes.",
            reply_to_message_id=mensagem.message_id,
        )

def enviar_desconto_carrinho(provider, url_carrinho, mensagem, id_mensagem_carregando):
    try:
        bot.delete_message(mensagem.chat.id, id_mensagem_carregando)
    except Exception:
        pass

    try:
        link_afiliado = provider.get_cart_discount_link(url_carrinho)
        if not link_afiliado:
            bot.send_message(
                mensagem.chat.id,
                "❌ Não consegui gerar o link de desconto para esse carrinho.",
                reply_to_message_id=mensagem.message_id,
            )
            return

        mensagem_desconto = f"Este é o link para o desconto no carrinho:\n{link_afiliado}"

        if os.path.exists(config.CART_IMAGE_PATH):
            with open(config.CART_IMAGE_PATH, "rb") as img:
                bot.send_photo(
                    mensagem.chat.id,
                    img,
                    caption=mensagem_desconto,
                    reply_to_message_id=mensagem.message_id,
                )
        else:
            bot.send_message(mensagem.chat.id, mensagem_desconto, reply_to_message_id=mensagem.message_id)
    except Exception as e:
        logging.error(f"[ERRO] Falha ao gerar link de carrinho: {e}")
        bot.send_message(
            mensagem.chat.id,
            "⚠️ Algo deu errado ao gerar o link do carrinho. Tente novamente em instantes.",
            reply_to_message_id=mensagem.message_id,
        )

# ====================== HANDLERS DO TELEGRAM ==========================
def registrar_handlers():
    @bot.message_handler(commands=["start"])
    def handle_start(mensagem):
        user_id = mensagem.from_user.id
        nome_usuario = mensagem.from_user.first_name

        if user_id in ADMIN_USER_IDS:
            menu = menu_admin
            mensagem_boas_vindas = f"🔐 Olá, {nome_usuario}!\n\nVocê está no menu administrador."
        else:
            menu = menu_padrao
            mensagem_boas_vindas = (
                f"👋 Olá, {nome_usuario}! Bem-vindo ao {config.BOT_DISPLAY_NAME}\n\n"
                "Envie um link de produto suportado para gerar seu desconto:\n\n"
                "1️⃣ Envie o link\n2️⃣ Aguarde o processamento\n3️⃣ Aproveite seus descontos!\n\n"
                "🔗 *Nossos canais:*"
            )

        if os.path.exists(config.WELCOME_IMAGE_PATH):
            with open(config.WELCOME_IMAGE_PATH, "rb") as foto:
                bot.send_photo(
                    mensagem.chat.id,
                    foto,
                    caption=mensagem_boas_vindas,
                    reply_markup=menu,
                    parse_mode="Markdown",
                    reply_to_message_id=mensagem.message_id,
                )
        else:
            bot.send_message(
                mensagem.chat.id,
                mensagem_boas_vindas,
                reply_markup=menu,
                parse_mode="Markdown",
                reply_to_message_id=mensagem.message_id,
            )

    @bot.message_handler(func=lambda m: True)
    def handle_mensagem(mensagem):
        try:
            url_produto = extrair_url_do_texto(mensagem.text)
            if not url_produto:
                bot.send_message(
                    mensagem.chat.id,
                    "❌ Não encontrei nenhum link na sua mensagem.",
                    reply_to_message_id=mensagem.message_id,
                )
                return

            provider = encontrar_provider(PROVIDERS_ATIVOS, url_produto)
            if not provider:
                bot.send_message(
                    mensagem.chat.id,
                    "❌ O link enviado não é de uma loja suportada por este bot.",
                    reply_to_message_id=mensagem.message_id,
                )
                return

            mensagem_carregando = bot.send_message(
                mensagem.chat.id,
                "⏳ Aguarde um momento, estamos preparando sua oferta...",
            )

            url_produto = provider.normalize_url(url_produto)

            if provider.is_cart_link(url_produto):
                enviar_desconto_carrinho(provider, url_produto, mensagem, mensagem_carregando.message_id)
            else:
                enviar_links_afiliados(provider, mensagem, mensagem_carregando.message_id, url_produto)
        except Exception as e:
            logging.error(f"[ERRO] Falha ao processar mensagem: {e}")
            bot.send_message(
                mensagem.chat.id,
                "⚠️ Ocorreu um erro ao processar sua mensagem. Tente novamente.",
                reply_to_message_id=mensagem.message_id,
            )

    logging.info("[OK] Handlers registrados com sucesso.")

# ====================== INICIALIZAÇÃO ==========================
def start_server():
    PORT = int(os.getenv("PORT", 8080))
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, WebhookHandler)
    logging.info(f"[OK] Servidor HTTP iniciado na porta {PORT}.")
    httpd.serve_forever()

def configurar_webhook():
    url_webhook = os.getenv("URL_WEBHOOK")
    if not url_webhook:
        logging.error("[ERRO] URL_WEBHOOK não configurado nas variáveis de ambiente.")
        return False
    try:
        import time
        bot.remove_webhook()
        time.sleep(1)
        sucesso = bot.set_webhook(url_webhook)
        if sucesso:
            logging.info(f"[OK] Webhook configurado: {url_webhook}")
            return True
        logging.error("[ERRO] Falha ao configurar webhook.")
        return False
    except Exception as e:
        logging.error(f"[ERRO] Exceção ao configurar webhook: {e}")
        return False

if __name__ == "__main__":
    logging.info("[INFO] Inicializando bot...")
    registrar_handlers()

    if configurar_webhook():
        start_server()
    else:
        logging.error("[ERRO] Bot não iniciou devido a problema no webhook.")
