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
    format="[%(asctime)s] %(levelname)s: %(message)s",
    stream=sys.stdout,
)

load_dotenv()

TOKEN = os.getenv("TOKEN_BOT")
if not TOKEN:
    logging.error("[ERRO] TOKEN_BOT não encontrado nas variáveis de ambiente.")
    exit(1)
bot = TeleBot(TOKEN, threaded=False)

try:
    api_aliexpress = AliexpressApi(
        os.getenv("CHAVE_APP"),
        os.getenv("SEGREDO_APP"),
        models.Language.PT,
        models.Currency.BRL,
        os.getenv("ID_RASTREAMENTO"),
    )
    logging.info("[OK] API do AliExpress configurada com sucesso.")
except Exception as e:
    logging.error(f"[ERRO] Falha ao configurar API do AliExpress: {e}")
    exit(1)

# ====================== MENUS ==========================
menu_padrao = types.InlineKeyboardMarkup(row_width=1)
botao_chat = types.InlineKeyboardButton("💬 Chat 💬", url=os.getenv("LINK_TELEGRAM_CHAT"))
botao_promocoes = types.InlineKeyboardButton("🔥 Promoções 🔥", url=os.getenv("LINK_TELEGRAM_OFERTAS"))
botao_youtube = types.InlineKeyboardButton("🎥 Youtube 🎥", url=os.getenv("LINK_YOUTUBE"))
menu_padrao.add(botao_chat, botao_promocoes, botao_youtube)

menu_admin = types.InlineKeyboardMarkup(row_width=1)
um = types.InlineKeyboardButton("1", url="https://s.click.aliexpress.com/e/_ol8VJ2T")
dois = types.InlineKeyboardButton("2", url="https://s.click.aliexpress.com/e/_DlCyg5Z")
tres = types.InlineKeyboardButton("3", url="https://s.click.aliexpress.com/e/_DBBkt9V")
quatro = types.InlineKeyboardButton("4", url="https://s.click.aliexpress.com/e/_DdcXZ2r")
cinco = types.InlineKeyboardButton("5", url="https://s.click.aliexpress.com/e/_DDs7W5D")
menu_admin.add(um, dois, tres, quatro, cinco, botao_chat, botao_promocoes, botao_youtube)

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

# ====================== FUNÇÕES DE NORMALIZAÇÃO ==========================
def normalizar_url_canonica(url):
    """
    Extrai o ID do produto e retorna a URL canônica no formato:
    https://www.aliexpress.com/item/<ID>.html

    Suporta:
    - /item/ID.html
    - productId, productIds, objectId
    - /ssr/ links (productIds)
    - links encurtados (s.click / a.aliexpress)
    """
    try:
        if not url:
            return url

        # Caso clássico: /item/123.html
        m = re.search(r"/item/(\d+)\.html", url)
        if m:
            product_id = m.group(1)
            return f"https://www.aliexpress.com/item/{product_id}.html"

        # Verifica parâmetros productIds / productId
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        for key in ("productIds", "productId", "objectId", "product_id"):
            if key in qs and qs[key]:
                product_id = re.search(r"(\d+)", qs[key][0])
                if product_id:
                    return f"https://www.aliexpress.com/item/{product_id.group(1)}.html"

        # Links SSR com productIds embutidos
        if "/ssr/" in url:
            m = re.search(r"productIds=(\d+)", url)
            if m:
                return f"https://www.aliexpress.com/item/{m.group(1)}.html"

        # Links encurtados
        if "a.aliexpress.com" in url or "s.click.aliexpress.com" in url:
            r = requests.get(url, allow_redirects=True, timeout=10)
            if r.url:
                return normalizar_url_canonica(r.url)

        return url
    except Exception as e:
        logging.warning(f"[WARN] Falha ao normalizar URL: {e}")
        return url

# ====================== FUNÇÕES PRINCIPAIS ==========================
def obter_links_afiliados(mensagem, id_mensagem, link_produto):
    try:

        link_produto = normalizar_url_canonica(link_produto)

        link_promocao = link_produto
        if "coin-index" not in link_produto:
            link_promocao = construir_link_promocao(link_produto)

        logging.info(f"[INFO] Link Produto Original: {link_produto}")
        logging.info(f"[INFO] Link Promocional: {link_promocao}")

        try:
            response_afiliados = api_aliexpress.get_affiliate_links(link_produto)
            logging.warning(response_afiliados)
        except Exception as e:
            logging.warning(f"[WARN] get_affiliate_links (afiliados) falhou: {e}")
            response_afiliados = None

        try:
            response_moedas = api_aliexpress.get_affiliate_links(link_promocao)
            logging.warning(response_moedas)
        except Exception as e:
            logging.warning(f"[WARN] get_affiliate_links (moedas) falhou: {e}")
            response_moedas = None

        def extrair_link_promocional(response):
            if not response:
                return None
            try:
                itens = list(response)
            except Exception:
                itens = [response]
            for item in itens:
                if hasattr(item, "promotion_link") and item.promotion_link:
                    return item.promotion_link
                if hasattr(item, "source_value") and item.source_value:
                    return item.source_value
                try:
                    d = getattr(item, "__dict__", None)
                    if isinstance(d, dict):
                        if "promotion_link" in d and d["promotion_link"]:
                            return d["promotion_link"]
                        if "source_value" in d and d["source_value"]:
                            return d["source_value"]
                except Exception:
                    pass
            return None

        link_afiliado = extrair_link_promocional(response_afiliados)
        link_moedas = extrair_link_promocional(response_moedas)

        titulo_produto = None
        imagem_produto = None
        try:
            timestamp = str(int(time.time() * 1000))
            detalhes_produto = api_aliexpress.get_products_details([
                timestamp,
                f"https://star.aliexpress.com/share/share.htm?platform=AE&businessType=ProductDetail&redirectUrl={link_produto}",
            ])
            if detalhes_produto and len(detalhes_produto) > 0:
                # esses campos podem existir dependendo do retorno
                titulo_produto = getattr(detalhes_produto[0], "product_title", None)
                imagem_produto = getattr(detalhes_produto[0], "product_main_image_url", None)
        except Exception as e:
            logging.warning(f"[WARN] get_products_details falhou: {e} — continuando sem título/imagem.")

        # ===== Remove mensagem de carregando (se existir) =====
        try:
            bot.delete_message(mensagem.chat.id, id_mensagem)
        except Exception:
            pass

        # ===== Monta legenda dinamicamente mostrando apenas links existentes =====
        partes = ["🛒 Seu produto com desconto está pronto:\n\n"]
        if titulo_produto:
            partes.append(f"{titulo_produto}\n\n")

        # só adiciona cada bloco se existir
        if link_moedas:
            partes.append(f"🔗 Link na aba de moedas:\n{link_moedas}\n\n")

        if link_afiliado:
            partes.append(f"🔗 Link direto do produto:\n{link_afiliado}\n\n")

        partes.append("👇 Me acompanhe nas redes sociais para mais descontos 👇")
        legenda_final = "".join(partes)

        # ===== Envio: se tiver imagem, tenta enviar como foto; senão envia texto =====
        if imagem_produto:
            try:
                bot.send_photo(
                    mensagem.chat.id,
                    imagem_produto,
                    caption=legenda_final,
                    reply_markup=menu_padrao,
                    reply_to_message_id=mensagem.message_id,
                )
            except Exception as e:
                logging.warning(f"[WARN] Falha ao enviar foto: {e} — enviando texto.")
                bot.send_message(
                    mensagem.chat.id,
                    legenda_final,
                    reply_markup=menu_padrao,
                    reply_to_message_id=mensagem.message_id,
                )
        else:
            bot.send_message(
                mensagem.chat.id,
                legenda_final,
                reply_markup=menu_padrao,
                reply_to_message_id=mensagem.message_id,
            )

    except Exception as e:
        bot.send_message(
            mensagem.chat.id,
            f"Algo deu errado \n {str(e)}",
            reply_to_message_id=mensagem.message_id,
        )
        logging.error(f"[ERRO] Falha ao obter links afiliados: {e}")

# ====================== FUNÇÕES DE URL ==========================
def extrair_url_do_texto(texto):
    padrao_url = r"https?://\S+|www\.\S+"
    urls = re.findall(padrao_url, texto)
    return urls[0] if urls else None

def construir_link_promocao(link_original):
    parametros = extrair_parametros_url(link_original)
    object_id = parametros.get("product_id", [None])[0]

    if not object_id:
        m = re.search(r"/item/(\d+).html", link_original)
        if m:
            object_id = m.group(1)

    if not object_id:
        return None

    return f"https://m.aliexpress.com/p/coin-index/index.html?_immersiveMode=true&productIds={object_id}"

def extrair_parametros_url(url):
    return parse_qs(urlparse(url).query)

def criar_url_com_parametros(url_base, parametros):
    return url_base + urlencode(parametros)

def obter_link_desconto_carrinho(link_carrinho, mensagem):
    try:
        link_carrinho_formatado = construir_link_promocao(link_carrinho)
        link_afiliado = api_aliexpress.get_affiliate_links(link_carrinho_formatado)[0].promotion_link

        mensagem_desconto = f"Este é o link para o desconto no carrinho:\n{link_afiliado}"

        caminho_imagem = "assets/bibi-1.jpg"
        with open(caminho_imagem, "rb") as img:
            bot.send_photo(
                mensagem.chat.id,
                img,
                caption=mensagem_desconto,
                reply_to_message_id=mensagem.message_id,
            )
    except Exception as e:
        bot.send_message(
            mensagem.chat.id,
            f"Algo deu errado \n{e}",
            reply_to_message_id=mensagem.message_id,
        )
        logging.error(f"[ERRO] Falha ao gerar link de carrinho: {e}")

# ====================== RESOLUÇÃO DE LINKS ==========================
def obter_url_final(url_encurtado):
    try:
        session = requests.Session()
        headers = {"User-Agent": "Mozilla/5.0 (compatible; TelegramBot/1.0)"}
        response = session.head(url_encurtado, headers=headers, allow_redirects=True, timeout=10)
        final_url = response.url

        if "redirect" in final_url or "share" in final_url or "aliexpress.com/item/" not in final_url:
            response = session.get(final_url, headers=headers, allow_redirects=True, timeout=10)
            final_url = response.url

        logging.info(f"[INFO] Link final resolvido: {final_url}")
        return final_url
    except Exception as e:
        logging.error(f"[ERRO] Falha ao resolver URL final: {e}")
        return url_encurtado

def extrair_redirect_url_recursiva(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    if "productIds" in query_params:
        product_id = query_params["productIds"][0]
        return f"https://www.aliexpress.com/item/{product_id}.html"

    while "redirectUrl" in query_params:
        redirect_url = unquote(query_params["redirectUrl"][0])
        parsed_url = urlparse(redirect_url)
        query_params = parse_qs(parsed_url.query)
        if "aliexpress.com/item/" in redirect_url:
            return redirect_url
        url = redirect_url

    return url

def resolver_link_ali(link_encurtado):
    try:
        final_url = obter_url_final(link_encurtado)
        resolved_url = extrair_redirect_url_recursiva(final_url)
        resolved_url = normalizar_url_canonica(resolved_url)
        if "aliexpress.com/item/" in resolved_url:
            logging.info(f"[OK] Link resolvido: {resolved_url}")
            return resolved_url
        else:
            logging.warning(f"[WARN] Não foi possível extrair link do produto. Retornando URL final.")
            return final_url
    except Exception as e:
        logging.error(f"[ERRO] Falha ao resolver link encurtado: {e}")
        return link_encurtado

# ====================== HANDLERS DO TELEGRAM ==========================
def registrar_handlers():
    @bot.message_handler(commands=["start"])
    def handle_start(mensagem):
        user_id = mensagem.from_user.id
        nome_usuario = mensagem.from_user.first_name

        if user_id == 5206185262:
            menu = menu_admin
            mensagem_boas_vindas = (
                f"🔐 Olá Papai {nome_usuario}!\n\n"
                "Você está no menu Admin.\n\n"
                "🛠 Enviar notificações\n📊 Ver estatísticas\n📦 Gerenciar promoções\n⚠️ Use com cuidado!"
            )
        else:
            menu = menu_padrao
            mensagem_boas_vindas = (
                f"👋 Olá, {nome_usuario}!\n\n"
                "Envie qualquer link do AliExpress para gerar:\n\n"
                "🔥 Link com desconto de moedas | ⚡ Link com desconto de afiliado\n\n"
                "1️⃣ Envie o link\n2️⃣ Aguarde o processamento\n3️⃣ Aproveite seus descontos!\n\n"
                "🔗 *Nossos canais:*"
            )

        with open("assets/bibi-2.jpg", "rb") as foto:
            bot.send_photo(
                mensagem.chat.id,
                foto,
                caption=mensagem_boas_vindas,
                reply_markup=menu,
                parse_mode="Markdown",
                reply_to_message_id=mensagem.message_id,
            )

    @bot.message_handler(func=lambda m: True)
    def handle_mensagem(mensagem):
        try:
            url_produto = extrair_url_do_texto(mensagem.text)
            mensagem_carregando = bot.send_message(
                mensagem.chat.id,
                "⏳ Aguarde um momento, estamos preparando sua oferta...",
            )

            if url_produto and "aliexpress.com" in url_produto:
                url_produto = normalizar_url_canonica(url_produto)
                if any(x in url_produto for x in ["s.click.aliexpress.com", "a.aliexpress.com"]):
                    url_produto = resolver_link_ali(url_produto)

                if "availableProductShopcartIds" in url_produto:
                    obter_link_desconto_carrinho(url_produto, mensagem)
                else:
                    obter_links_afiliados(mensagem, mensagem_carregando.message_id, url_produto)
            else:
                bot.delete_message(mensagem.chat.id, mensagem_carregando.message_id)
                bot.send_message(
                    mensagem.chat.id,
                    "❌ O link enviado não é válido!\nPor favor, envie um link do AliExpress.",
                    parse_mode="HTML",
                    reply_to_message_id=mensagem.message_id,
                )
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

if __name__ == "__main__":
    logging.info("[INFO] Inicializando bot...")
    registrar_handlers()

    if configurar_webhook():
        start_server()
    else:
        logging.error("[ERRO] Bot não iniciou devido a problema no webhook.")
