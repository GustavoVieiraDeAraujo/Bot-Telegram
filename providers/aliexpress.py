import os
import re
import time
import logging
import requests
from urllib.parse import urlparse, parse_qs, unquote

from aliexpress_api import AliexpressApi, models

from .base import AffiliateProvider


class AliExpressProvider(AffiliateProvider):
    name = "aliexpress"

    #: variaveis de ambiente que este provider precisa para funcionar
    ENV_REQUERIDAS = ("ALIEXPRESS_CHAVE_APP", "ALIEXPRESS_SEGREDO_APP", "ALIEXPRESS_ID_RASTREAMENTO")

    def __init__(self, app_key, app_secret, tracking_id, language=None, currency=None):
        self.client = AliexpressApi(
            app_key,
            app_secret,
            language or models.Language.PT,
            currency or models.Currency.BRL,
            tracking_id,
        )

    @classmethod
    def from_env(cls):
        """Constroi o provider a partir das variaveis de ambiente. Retorna None se alguma faltar."""
        valores = [os.getenv(nome) for nome in cls.ENV_REQUERIDAS]
        if not all(valores):
            faltando = [nome for nome, valor in zip(cls.ENV_REQUERIDAS, valores) if not valor]
            logging.warning(f"[WARN] Provider 'aliexpress' nao ativado, faltam variaveis: {', '.join(faltando)}")
            return None
        return cls(*valores)

    # ------------------------------------------------------------------
    # Identificacao
    # ------------------------------------------------------------------
    def matches(self, url):
        if not url:
            return False
        return "aliexpress.com" in url

    def is_cart_link(self, url):
        return bool(url) and "availableProductShopcartIds" in url

    # ------------------------------------------------------------------
    # Normalizacao de URL
    # ------------------------------------------------------------------
    def normalize_url(self, url):
        """
        Extrai o ID do produto e retorna a URL canonica no formato:
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

            m = re.search(r"/item/(\d+)\.html", url)
            if m:
                return f"https://www.aliexpress.com/item/{m.group(1)}.html"

            parsed = urlparse(url)
            qs = parse_qs(parsed.query)
            for key in ("productIds", "productId", "objectId", "product_id"):
                if key in qs and qs[key]:
                    product_id = re.search(r"(\d+)", qs[key][0])
                    if product_id:
                        return f"https://www.aliexpress.com/item/{product_id.group(1)}.html"

            if "/ssr/" in url:
                m = re.search(r"productIds=(\d+)", url)
                if m:
                    return f"https://www.aliexpress.com/item/{m.group(1)}.html"

            if "a.aliexpress.com" in url or "s.click.aliexpress.com" in url:
                r = requests.get(url, allow_redirects=True, timeout=10)
                if r.url:
                    return self.normalize_url(r.url)

            if any(x in url for x in ("s.click.aliexpress.com", "a.aliexpress.com")):
                url = self._resolver_link_encurtado(url)

            return url
        except Exception as e:
            logging.warning(f"[WARN] Falha ao normalizar URL do AliExpress: {e}")
            return url

    def _resolver_link_encurtado(self, link_encurtado):
        try:
            final_url = self._obter_url_final(link_encurtado)
            resolved_url = self._extrair_redirect_url_recursiva(final_url)
            resolved_url = self.normalize_url(resolved_url)
            if "aliexpress.com/item/" in resolved_url:
                logging.info(f"[OK] Link resolvido: {resolved_url}")
                return resolved_url
            logging.warning("[WARN] Nao foi possivel extrair link do produto. Retornando URL final.")
            return final_url
        except Exception as e:
            logging.error(f"[ERRO] Falha ao resolver link encurtado: {e}")
            return link_encurtado

    def _obter_url_final(self, url_encurtado):
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

    def _extrair_redirect_url_recursiva(self, url):
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

    def _construir_link_promocao(self, link_original):
        parametros = parse_qs(urlparse(link_original).query)
        object_id = parametros.get("product_id", [None])[0]

        if not object_id:
            m = re.search(r"/item/(\d+)\.html", link_original)
            if m:
                object_id = m.group(1)

        if not object_id:
            return None

        return f"https://m.aliexpress.com/p/coin-index/index.html?_immersiveMode=true&productIds={object_id}"

    # ------------------------------------------------------------------
    # Links de afiliado
    # ------------------------------------------------------------------
    def get_affiliate_links(self, url):
        link_produto = self.normalize_url(url)

        link_promocao = link_produto
        if "coin-index" not in link_produto:
            link_promocao = self._construir_link_promocao(link_produto)

        logging.info(f"[INFO] Link Produto Original: {link_produto}")
        logging.info(f"[INFO] Link Promocional: {link_promocao}")

        response_afiliados = self._chamar_get_affiliate_links(link_produto)
        response_moedas = self._chamar_get_affiliate_links(link_promocao) if link_promocao else None

        return {
            "direct": self._extrair_link_promocional(response_afiliados),
            "promo": self._extrair_link_promocional(response_moedas),
        }

    def _chamar_get_affiliate_links(self, url):
        if not url:
            return None
        try:
            response = self.client.get_affiliate_links(url)
            logging.warning(response)
            return response
        except Exception as e:
            logging.warning(f"[WARN] get_affiliate_links falhou para {url}: {e}")
            return None

    @staticmethod
    def _extrair_link_promocional(response):
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
            d = getattr(item, "__dict__", None)
            if isinstance(d, dict):
                if d.get("promotion_link"):
                    return d["promotion_link"]
                if d.get("source_value"):
                    return d["source_value"]
        return None

    def get_product_details(self, url):
        link_produto = self.normalize_url(url)
        titulo_produto = None
        imagem_produto = None
        try:
            timestamp = str(int(time.time() * 1000))
            detalhes_produto = self.client.get_products_details([
                timestamp,
                f"https://star.aliexpress.com/share/share.htm?platform=AE&businessType=ProductDetail&redirectUrl={link_produto}",
            ])
            if detalhes_produto and len(detalhes_produto) > 0:
                titulo_produto = getattr(detalhes_produto[0], "product_title", None)
                imagem_produto = getattr(detalhes_produto[0], "product_main_image_url", None)
        except Exception as e:
            logging.warning(f"[WARN] get_products_details falhou: {e} — continuando sem titulo/imagem.")
        return titulo_produto, imagem_produto

    # ------------------------------------------------------------------
    # Carrinho com desconto (recurso especifico do AliExpress)
    # ------------------------------------------------------------------
    def get_cart_discount_link(self, url):
        link_formatado = self._construir_link_promocao(url)
        if not link_formatado:
            return None
        response = self._chamar_get_affiliate_links(link_formatado)
        return self._extrair_link_promocional(response)
