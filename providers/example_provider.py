"""
Modelo de provider novo. Copie este arquivo, implemente os metodos e
registre a classe em providers/__init__.py (dicionario PROVIDERS_DISPONIVEIS)
para o bot passar a reconhecer links dessa rede de afiliados.

Nao e uma integracao funcional — e so o esqueleto do contrato que
providers/base.py exige.
"""

from .base import AffiliateProvider


class ExampleProvider(AffiliateProvider):
    name = "example"

    def matches(self, url):
        # Retorne True quando a URL pertencer a essa rede de afiliados,
        # ex.: "meusite.com" in url
        raise NotImplementedError

    def normalize_url(self, url):
        # Extraia o identificador do produto e monte a URL canonica
        raise NotImplementedError

    def get_affiliate_links(self, url):
        # Chame a API de afiliados da rede e retorne algo como:
        # {"direct": "https://...", "promo": None}
        raise NotImplementedError

    def get_product_details(self, url):
        # Retorne (titulo, url_da_imagem); qualquer um pode ser None
        raise NotImplementedError
