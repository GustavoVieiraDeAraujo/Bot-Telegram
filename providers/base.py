from abc import ABC, abstractmethod


class AffiliateProvider(ABC):
    """
    Contrato que qualquer rede de afiliados precisa implementar para ser
    plugada no bot. Um provider cuida de tudo que é especifico da rede
    (formato de link, chamadas de API); o bot.py so conhece essa interface.
    """

    #: identificador curto usado em PROVIDERS no .env (ex.: "aliexpress")
    name = "generic"

    @abstractmethod
    def matches(self, url: str) -> bool:
        """Retorna True se este provider sabe lidar com a URL recebida."""
        raise NotImplementedError

    @abstractmethod
    def normalize_url(self, url: str) -> str:
        """Converte a URL (direta, encurtada, com parametros extras) para a URL canonica do produto."""
        raise NotImplementedError

    @abstractmethod
    def get_affiliate_links(self, url: str) -> dict:
        """
        Retorna um dict com os links de desconto disponiveis, ex.:
        {"direct": "https://...", "promo": "https://..." ou None}
        """
        raise NotImplementedError

    @abstractmethod
    def get_product_details(self, url: str) -> tuple:
        """Retorna (titulo, url_da_imagem); qualquer um dos dois pode ser None."""
        raise NotImplementedError

    def get_cart_discount_link(self, url: str) -> str:
        """
        Extensao opcional: providers que tem o conceito de "carrinho com
        desconto" (como o AliExpress) sobrescrevem este metodo. O padrao
        e nao suportar, retornando None.
        """
        return None

    def is_cart_link(self, url: str) -> bool:
        """Extensao opcional: identifica se a URL e um link de carrinho, nao de produto."""
        return False
