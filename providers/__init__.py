import os
import logging

from .base import AffiliateProvider
from .aliexpress import AliExpressProvider

# Registro dos providers conhecidos pelo bot. Para adicionar uma rede nova:
# 1. Crie providers/sua_rede.py com uma classe que herda de AffiliateProvider
#    (veja providers/example_provider.py como modelo) e um classmethod from_env().
# 2. Registre a classe aqui.
# 3. Inclua o nome em PROVIDERS no .env.
PROVIDERS_DISPONIVEIS = {
    "aliexpress": AliExpressProvider,
}


def carregar_providers_ativos():
    """
    Le PROVIDERS do ambiente (nomes separados por virgula) e instancia,
    via from_env(), cada provider correspondente que tiver as credenciais
    configuradas. Providers sem credenciais sao pulados com um aviso.
    """
    nomes = [n.strip() for n in os.getenv("PROVIDERS", "aliexpress").split(",") if n.strip()]
    ativos = []
    for nome in nomes:
        classe = PROVIDERS_DISPONIVEIS.get(nome)
        if not classe:
            logging.warning(f"[WARN] Provider '{nome}' listado em PROVIDERS mas nao existe em providers/__init__.py")
            continue
        instancia = classe.from_env()
        if instancia:
            ativos.append(instancia)
            logging.info(f"[OK] Provider '{nome}' ativado.")
    return ativos


def encontrar_provider(providers_ativos, url):
    """Retorna o primeiro provider ativo que sabe lidar com a URL, ou None."""
    for provider in providers_ativos:
        if provider.matches(url):
            return provider
    return None
