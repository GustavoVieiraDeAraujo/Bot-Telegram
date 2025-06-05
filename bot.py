import os
import re
import json
import time
import pprint
import urllib
import logging
from dotenv import load_dotenv
from telebot import TeleBot, types
from urllib.parse import urlparse, parse_qs
from aliexpress_api import AliexpressApi, models
from http.server import BaseHTTPRequestHandler, HTTPServer

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Inicializa o bot do Telegram com o token da variável de ambiente
TOKEN = os.getenv('TOKEN_BOT')
if not TOKEN:
    print("[ERRO] TOKEN_BOT não encontrado nas variáveis de ambiente.")
    exit(1)
bot = TeleBot(TOKEN, threaded=False)

# Configura a API do AliExpress
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

# Configuração dos teclados (mantida igual)
teclado_inicial = types.InlineKeyboardMarkup(row_width=1)
botao_jogos = types.InlineKeyboardButton("⭐️Jogos de colecionar moedas⭐️", callback_data="jogos")
botao_desconto = types.InlineKeyboardButton("⭐️Desconto monetário em produtos da cesta 🛒⭐️", callback_data='clique')
botao_tutorial = types.InlineKeyboardButton("🎬 Veja como o bot funciona 🎬", url=os.getenv('LINK_CANAL'))
teclado_inicial.add(botao_jogos, botao_desconto, botao_tutorial)

teclado_padrao = types.InlineKeyboardMarkup(row_width=1)
botao_jogos_padrao = types.InlineKeyboardButton("⭐️Jogos de colecionar moedas⭐️", callback_data="jogos")
botao_desconto_padrao = types.InlineKeyboardButton("⭐️Desconto monetário em produtos da cesta 🛒⭐️", callback_data='clique')
botao_inscrever = types.InlineKeyboardButton("❤️ Inscreva-se no canal para mais promoções ❤️", url=os.getenv('LINK_CANAL'))
teclado_padrao.add(botao_jogos_padrao, botao_desconto_padrao, botao_inscrever)

teclado_jogos = types.InlineKeyboardMarkup(row_width=1)
botao_revisao_diaria = types.InlineKeyboardButton(" ⭐️ Página de revisão diária e coleta de pontos ⭐️", url="https://s.click.aliexpress.com/e/_ol8VJ2T")
botao_merge_boss = types.InlineKeyboardButton("⭐️ Jogo Merge boss ⭐️", url="https://s.click.aliexpress.com/e/_DlCyg5Z")
botao_fazenda_fantastica = types.InlineKeyboardButton("⭐️ Jogo Fantastic Farm ⭐️", url="https://s.click.aliexpress.com/e/_DBBkt9V")
botao_gire_ganhe = types.InlineKeyboardButton("⭐️ Jogo Vire e Ganhe ⭐️", url="https://s.click.aliexpress.com/e/_DdcXZ2r")
botao_gogo_match = types.InlineKeyboardButton("⭐️ Jogo GoGo Match ⭐️", url="https://s.click.aliexpress.com/e/_DDs7W5D")
teclado_jogos.add(botao_revisao_diaria, botao_merge_boss, botao_fazenda_fantastica, botao_gire_ganhe, botao_gogo_match)

# Funções auxiliares (mantidas igual)

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
        links_afiliados = api_aliexpress.get_affiliate_links(
            f'{link_produto}?utm_source={codigo_rastreamento}&sourceType=620&improveDiscount=Y&BuyNow=true'
        )
        
        pprint.pp(links_afiliados)
        link_afiliado = link_super = link_limitado = links_afiliados[0].promotion_link

        try:
            timestamp = str(int(float("%.2f" % (float(time.time()))) * 1000))
            detalhes_produto = api_aliexpress.get_products_details([
                timestamp,
                f'https://star.aliexpress.com/share/share.htm?platform=AE&businessType=ProductDetail&redirectUrl={link_produto}'
            ])
            
            pprint.pp(detalhes_produto)
            preco_produto = detalhes_produto[0].target_sale_price
            titulo_produto = detalhes_produto[0].product_title
            imagem_produto = detalhes_produto[0].product_main_image_url
            
            bot.delete_message(mensagem.chat.id, id_mensagem)
            
            bot.send_photo(
                mensagem.chat.id,
                imagem_produto,
                caption=(
                    " \nSeu produto é: 🔥 \n"
                    f"{titulo_produto} 🛍 \n"
                    f"Preço do produto: {preco_produto} 💵\n"
                    f"\nLink {link_afiliado}"
                ),
                reply_markup=teclado_padrao
            )

        except Exception as e:
            bot.delete_message(mensagem.chat.id, id_mensagem)
            bot.send_message(
                mensagem.chat.id, 
                (
                    "Compare preços e compre 🔥 \n"
                    "💰 Exibição de moeda (preço final na finalização da compra): \n"
                    f"Link {link_afiliado} \n"
                    f"💎 Super oferta: \n"
                    f"Link {link_super} \n"
                    f"♨️ Oferta limitada: \n"
                    f"Link {link_limitado} \n\n"
                    "#PromocaoAliXpress ✅"
                ),
                reply_markup=teclado_padrao
            )

    except Exception as e:
        bot.send_message(
            mensagem.chat.id, 
            "Algo deu errado 🤷🏻‍♂️ \n " + str(e)
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
    return url_base + urllib.parse.urlencode(parametros)

def obter_link_desconto_carrinho(link_carrinho, mensagem):
    try:
        link_carrinho_formatado = construir_link_carrinho(link_carrinho)
        link_afiliado = api_aliexpress.get_affiliate_links(link_carrinho_formatado)[0].promotion_link

        mensagem_desconto = (
            f"Este é o link para o desconto no carrinho. \n"
            f"{str(link_afiliado)}"
        )

        imagem_carrinho = "https://picsum.photos/1022/771"
        bot.send_photo(mensagem.chat.id, imagem_carrinho, caption=mensagem_desconto)

    except Exception as e:
        bot.send_message(mensagem.chat.id, f"Algo deu errado 🤷🏻‍♂️ \n{e}")

def registrar_handlers():
    """
    Registra todos os handlers do bot:
    - Comandos (/start, etc)
    - Callback queries (botões)
    - Mensagens de texto
    """
    
    @bot.message_handler(commands=['start'])
    def handle_start(mensagem):
        print(f"[INFO] Comando /start recebido do usuário {mensagem.from_user.id}")
        bot.send_message(
            mensagem.chat.id,
            "👋 Olá! Seja bem-vindo!\nEscolha uma das opções abaixo:",
            reply_markup=teclado_padrao
        )

    @bot.callback_query_handler(func=lambda call: True)
    def handle_callback_query(chamada):
        print(f"[INFO] Callback query recebida: {chamada.data}")
        try:
            if chamada.data == 'jogos':
                bot.send_message(chamada.message.chat.id, "Buscando informações...")
                url_imagem_jogos = "https://picsum.photos/784/449"
                bot.send_photo(
                    chamada.message.chat.id,
                    url_imagem_jogos,
                    caption=(
                        "⭐️Jogos de colecionar moedas⭐️\n"
                        "Reúna moedas em vários jogos. O valor de cada moeda é igual a R$0,01. \n\n"
                        "💰Você pode trocar moedas acumuladas por desconto em produtos no AliExpress."
                    ),
                    reply_markup=teclado_jogos
                )

            elif chamada.data == 'clique':
                url_desconto_carrinho = "https://s.click.aliexpress.com/e/_Ddcx7vA"
                bot.send_message(
                    chamada.message.chat.id,
                    f"Seu link para desconto no carrinho: \n{url_desconto_carrinho}",
                    reply_markup=teclado_padrao
                )

        except Exception as e:
            print(f"[ERRO] Falha ao processar callback query: {e}")
            bot.send_message(
                chamada.message.chat.id,
                "⚠️ Erro interno ao processar sua solicitação."
            )

    @bot.message_handler(func=lambda m: True)
    def handle_mensagem(mensagem):
        print(f"[INFO] Mensagem recebida do usuário {mensagem.from_user.id}")
        
        if mensagem.text.startswith("/"):
            return
            
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