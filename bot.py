"""
Bot de Telegram para obtenção de links de afiliados e promoções no AliExpress
"""

# ========== IMPORTANDO BIBLIOTECAS E INICIANDO BOT E API  ==========

import re
import os
import time
import pprint
import json
import urllib
import telebot
from telebot import types
from dotenv import load_dotenv
from keep_alive import keep_alive
from urllib.parse import urlparse, parse_qs
from aliexpress_api import AliexpressApi, models

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Inicializa o bot do Telegram com o token da variável de ambiente
bot = telebot.TeleBot(os.getenv('TOKEN_BOT'))

# Configura a API do AliExpress com as credenciais
api_aliexpress = AliexpressApi(
    os.getenv('CHAVE_APP'), 
    os.getenv('SEGREDO_APP'),
    models.Language.PT, 
    models.Currency.BRL, 
    os.getenv('ID_RASTREAMENTO')
)

# ========== CONFIGURAÇÃO DOS TECLADOS ==========

# === Teclado inicial ===
teclado_inicial = types.InlineKeyboardMarkup(row_width=1)

botao_jogos = types.InlineKeyboardButton(
    "⭐️Jogos de colecionar moedas⭐️",
    callback_data="jogos"
)
botao_desconto = types.InlineKeyboardButton(
    "⭐️Desconto monetário em produtos da cesta 🛒⭐️",
    callback_data='clique'
)
botao_tutorial = types.InlineKeyboardButton(
    "🎬 Veja como o bot funciona 🎬",
    url=os.getenv('LINK_CANAL'))
botao_primeira_compra = types.InlineKeyboardButton(
    "💰 Desconto exclusivo de até 70% na primeira compra 💰",
    url=os.getenv('LINK_COMPARTILHAR_GANHAR')
)

teclado_inicial.add(botao_jogos, botao_desconto, botao_tutorial, botao_primeira_compra)

# === Teclado padrão ===
teclado_padrao = types.InlineKeyboardMarkup(row_width=1)

botao_jogos_padrao = types.InlineKeyboardButton(
    "⭐️Jogos de colecionar moedas⭐️",
    callback_data="jogos"
)
botao_desconto_padrao = types.InlineKeyboardButton(
    "⭐️Desconto monetário em produtos da cesta 🛒⭐️",
    callback_data='clique'
)
botao_inscrever = types.InlineKeyboardButton(
    "❤️ Inscreva-se no canal para mais promoções ❤️",
    url=os.getenv('LINK_CANAL')
)

teclado_padrao.add(botao_jogos_padrao, botao_desconto_padrao, botao_inscrever)

# === Teclado coleta de moedas ===
teclado_jogos = types.InlineKeyboardMarkup(row_width=1)

botao_revisao_diaria = types.InlineKeyboardButton(
    " ⭐️ Página de revisão diária e coleta de pontos ⭐️",
    url="https://s.click.aliexpress.com/e/_ol8VJ2T"
)
botao_merge_boss = types.InlineKeyboardButton(
    "⭐️ Jogo Merge boss ⭐️", 
    url="https://s.click.aliexpress.com/e/_DlCyg5Z"
)
botao_fazenda_fantastica = types.InlineKeyboardButton(
    "⭐️ Jogo Fantastic Farm ⭐️",
    url="https://s.click.aliexpress.com/e/_DBBkt9V"
)
botao_gire_ganhe = types.InlineKeyboardButton(
    "⭐️ Jogo Vire e Ganhe ⭐️",
    url="https://s.click.aliexpress.com/e/_DdcXZ2r"
)
botao_gogo_match = types.InlineKeyboardButton(
    "⭐️ Jogo GoGo Match ⭐️", 
    url="https://s.click.aliexpress.com/e/_DDs7W5D"
)

teclado_jogos.add(botao_revisao_diaria, botao_merge_boss, botao_fazenda_fantastica, botao_gire_ganhe, botao_gogo_match)

# ========== Funções Auxiliriares ==========

def obter_links_afiliados(mensagem, id_mensagem, link_produto):
    """
    Obtém e envia links de afiliados para um produto do AliExpress.
    
    Args:
        mensagem: Objeto de mensagem do Telegram.
        link_produto: URL do produto no AliExpress.
        id_mensagem: ID da mensagem a ser deletada/atualizada.
    """
    try:
        codigo_rastreamento = os.getenv('ID_RASTREAMENTO')
        links_afiliados = api_aliexpress.get_affiliate_links(
            f'{link_produto}?utm_source={codigo_rastreamento}&sourceType=620&improveDiscount=Y&BuyNow=true'
        )
        
        pprint.pp(links_afiliados)
        link_afiliado = link_super = link_limitado = links_afiliados[0].promotion_link

        try:
            # Obtém detalhes do produto (imagem, preço, título)
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
            
            # Envia a mensagem com a imagem e informações do produto
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
            # Caso falhe ao obter detalhes, envia apenas os links
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
            "Algo deu errado 🤷🏻‍♂️ \n " + str(link_limitado)
        )

def extrair_url_do_texto(texto):
    """
    Extrai a primeira URL encontrada em um texto.
    
    Args:
        texto: Texto contendo possíveis URLs.
        
    Returns:
        str: A primeira URL encontrada ou None se não houver.
    """
    padrao_url = r'https?://\S+|www\.\S+'
    urls = re.findall(padrao_url, texto)
    return urls[0] if urls else None

def construir_link_carrinho(link_original):
    """
    Constrói um link de carrinho de compras a partir de um link de produto.
    
    Args:
        link_original: URL do produto no AliExpress.
        
    Returns:
        str: URL formatada para o carrinho de compras.
    """
    parametros = extrair_parametros_url(link_original)
    url_base_carrinho = "https://www.aliexpress.com/p/trade/confirm.html?"
    parametros_carrinho = {
        "availableProductShopcartIds": ",".join(parametros["availableProductShopcartIds"]),
        "extraParams": json.dumps(
            {"channelInfo": {"sourceType": "620"}}, 
            separators=(',', ':')
        )
    }
    return criar_url_com_parametros(url_base_carrinho, parametros_carrinho)

def extrair_parametros_url(url):
    """
    Extrai os parâmetros de query de uma URL.
    
    Args:
        url: URL a ser analisada.
        
    Returns:
        dict: Dicionário com os parâmetros da query string.
    """
    url_analisada = urlparse(url)
    return parse_qs(url_analisada.query)

def criar_url_com_parametros(url_base, parametros):
    """
    Cria uma URL com parâmetros de query string.
    
    Args:
        url_base: URL base sem parâmetros.
        parametros: Dicionário com os parâmetros.
        
    Returns:
        str: URL completa com query string.
    """
    return url_base + urllib.parse.urlencode(parametros)

def obter_link_desconto_carrinho(link_carrinho, mensagem):
    """
    Obtém e envia link de afiliado para o carrinho de compras.
    
    Args:
        link_carrinho: URL do carrinho de compras.
        mensagem: Objeto de mensagem do Telegram.
    """
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
        bot.send_message(mensagem.id, "Algo deu errado 🤷🏻‍♂️")

@bot.message_handler(func=lambda mensagem: True)
def manipular_link_produto(mensagem):
    """
    Manipula mensagens contendo links de produtos do AliExpress.
    
    Args:
        mensagem: Objeto de mensagem do Telegram.
    """
    url_produto = extrair_url_do_texto(mensagem.text)
    mensagem_carregando = bot.send_message(
        mensagem.chat.id,
        'Aguarde um momento, as ofertas estão sendo preparadas ⏳'
    )
    
    if url_produto and "aliexpress.com" in url_produto:
        if "p/shoppingcart" in mensagem.text.lower():
            return
            
        if "availableProductShopcartIds".lower() in mensagem.text.lower():
            obter_link_desconto_carrinho(url_produto, mensagem)
            return
            
        obter_links_afiliados(mensagem, mensagem_carregando.message_id, url_produto)
    else:
        bot.delete_message(mensagem.chat.id, mensagem_carregando.message_id)
        bot.send_message(
            mensagem.chat.id,
            "O link é inválido! Verifique o link do produto ou tente novamente.\n"
            "Envie apenas o link sem o título do produto.",
            parse_mode='HTML'
        )

@bot.callback_query_handler(func=lambda chamada: True)
def manipular_botao_jogos(chamada):
    """
    Manipula o clique no botão de jogos, mostrando opções de jogos para coleta de moedas.
    
    Args:
        chamada: Objeto de callback da interação com o botão inline.
    """
    bot.send_message(chamada.message.chat.id, "..")

    url_imagem_jogos = "https://picsum.photos/784/449"
    bot.send_photo(
        chamada.message.chat.id,
        url_imagem_jogos,
        caption=(
            "Links para jogos de colecionar moedas para usar para reduzir o preço de alguns produtos. "
            "Faça login diariamente para obter o maior número possível por dia 👇"
        ),
        reply_markup=teclado_jogos
    )

@bot.message_handler(commands=['start'])
def boas_vindas(mensagem):
    """
    Envia mensagem de boas-vindas quando o usuário inicia o bot.
    
    Args:
        mensagem: Objeto de mensagem do Telegram contendo informações do chat.
    """
    bot.send_message(
        mensagem.chat.id,
        "Por favor, envie-nos o link do produto que deseja comprar para que possamos lhe oferecer o melhor preço 👌 \n",
        reply_markup=teclado_inicial
    )

@bot.callback_query_handler(func=lambda chamada: chamada.data == 'clique')
def manipular_botao_desconto(chamada):
    """
    Manipula o clique no botão de desconto, mostrando instruções para obter descontos.
    
    Args:
        chamada: Objeto de callback da interação com o botão inline.
    """
    texto_instrucoes = (
        "✅1- Entre no carrinho por aqui:\n"
        " https://s.click.aliexpress.com/e/_opGCtMf \n"
        "✅2- Escolha os produtos que deseja reduzir o preço\n"
        "✅3- Clique no botão de pagamento para ser redirecionado para a página de confirmação\n"
        "✅4- Clique no ícone acima e copie o link aqui no bot para obter o link de desconto"
    )

    url_imagem_carrinho = "https://picsum.photos/1022/771"
    bot.send_photo(
        chamada.message.chat.id,
        url_imagem_carrinho,
        caption=texto_instrucoes,
        reply_markup=teclado_padrao
    )

# ========== INICIALIZAÇÃO DO BOT ==========

# Mantém a aplicação ativa
keep_alive()

# Inicia o bot com configurações de polling
bot.infinity_polling(timeout=10, long_polling_timeout=5, none_stop=True)