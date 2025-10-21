import os
import json
import logging


def obter_admin_user_ids():
    """Le ADMIN_USER_IDS do ambiente (ids numericos separados por virgula) e retorna uma lista de int."""
    bruto = os.getenv("ADMIN_USER_IDS", "")
    ids = []
    for parte in bruto.split(","):
        parte = parte.strip()
        if not parte:
            continue
        try:
            ids.append(int(parte))
        except ValueError:
            logging.warning(f"[WARN] Valor invalido em ADMIN_USER_IDS, ignorado: '{parte}'")
    return ids


def obter_links_rapidos_admin():
    """
    Le a lista de botoes extras do menu administrador de um arquivo JSON
    (padrao: config/admin_links.json), no formato:
    [{"label": "Produto 1", "url": "https://..."}, ...]
    Se o arquivo nao existir, retorna uma lista vazia (o bot funciona normalmente,
    so sem esses botoes extras).
    """
    caminho = os.getenv("ADMIN_LINKS_PATH", "config/admin_links.json")
    if not os.path.exists(caminho):
        return []
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
        return [item for item in dados if item.get("label") and item.get("url")]
    except Exception as e:
        logging.warning(f"[WARN] Falha ao ler {caminho}: {e} — menu administrador ficara sem botoes extras.")
        return []


WELCOME_IMAGE_PATH = os.getenv("WELCOME_IMAGE_PATH", "")
CART_IMAGE_PATH = os.getenv("CART_IMAGE_PATH", "")
BOT_DISPLAY_NAME = os.getenv("BOT_DISPLAY_NAME", "Bot de Afiliados")
