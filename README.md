# Bot de Afiliados para Telegram

Bot de Telegram que recebe links de produtos enviados por usuarios em uma conversa ou grupo e responde com links de afiliado, junto com titulo e imagem do produto quando disponiveis. A geracao dos links e feita por "providers" plugaveis, um por rede de afiliados: o repositorio ja vem com um provider funcional para o AliExpress, e novas redes podem ser adicionadas sem alterar o restante do bot. Escrito em Python, roda como um servidor HTTP que recebe atualizacoes do Telegram via webhook (nao polling).

---

## Sumario

- [Colaboradores](#colaboradores)
- [Tecnologias](#tecnologias)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Requisitos](#requisitos)
- [Configuracao](#configuracao)
- [Como Executar](#como-executar)
- [Arquitetura](#arquitetura)

---

## Colaboradores

| Nome | Papel |
| --- | --- |
| Gustavo Vieira de Araújo | Desenvolvedor |

---

## Tecnologias

| Tecnologia | Uso |
| --- | --- |
| Python 3.10+ | Linguagem principal do bot. |
| pyTelegramBotAPI (`telebot`) | Cliente da API do Telegram: registro de handlers, teclados inline, envio de mensagens/fotos. |
| python-aliexpress-api | Cliente da API oficial de afiliados do AliExpress, usado pelo provider `aliexpress`. |
| python-dotenv | Carrega as variaveis de ambiente do arquivo `.env` em tempo de execucao. |
| requests | Resolucao de links encurtados e chamadas HTTP diretas (usado pelo provider `aliexpress`). |
| `http.server` (biblioteca padrao) | Servidor HTTP minimalista que recebe o webhook do Telegram (sem framework web). |

---

## Estrutura do Projeto

| Diretorio / Arquivo | Descricao |
| --- | --- |
| `bot.py` | Ponto de entrada: handlers do Telegram, montagem dos menus e servidor HTTP do webhook. Nao conhece detalhes de nenhuma rede de afiliados especifica. |
| `config.py` | Leitura das variaveis de configuracao do bot (administradores, nomes exibidos, caminhos de imagem) e dos botoes extras do menu administrador. |
| `providers/base.py` | Contrato `AffiliateProvider` que toda rede de afiliados precisa implementar. |
| `providers/aliexpress.py` | Provider funcional para o AliExpress (normalizacao de link, links de afiliado, carrinho com desconto). |
| `providers/example_provider.py` | Modelo de provider novo, sem implementacao real — copie e implemente pra adicionar outra rede de afiliados. |
| `providers/__init__.py` | Registro dos providers disponiveis e logica de ativacao a partir da variavel `PROVIDERS`. |
| `config/admin_links.example.json` | Modelo dos botoes extras do menu administrador. Copie para `config/admin_links.json` (ignorado pelo git) e edite com seus links. |
| `docs/architecture.svg` | Diagrama do fluxo de uma mensagem, do usuario no Telegram ate a API do provider ativo. |
| `.env.save` | Modelo das variaveis de ambiente esperadas. Deve ser copiado para `.env` e preenchido com valores reais (nunca commitado). |
| `.gitignore` | Ignora `.env`, `*.pyc`, `venv/` e `config/admin_links.json`. |
| `requirements.txt` | Dependencias Python fixadas por versao. |

---

## Requisitos

| Dependencia | Versao | Instalacao |
| --- | --- | --- |
| Python | 3.10 ou superior | [python.org/downloads](https://www.python.org/downloads) |
| pip | qualquer recente | incluido na instalacao do Python |
| Bot no Telegram | - | criado via [@BotFather](https://t.me/BotFather), gera o `TOKEN_BOT` |
| Credenciais de ao menos um provider configurado em `PROVIDERS` | - | ex.: conta de afiliado AliExpress, que fornece `ALIEXPRESS_CHAVE_APP`, `ALIEXPRESS_SEGREDO_APP` e `ALIEXPRESS_ID_RASTREAMENTO` |
| URL publica HTTPS | - | necessaria para o Telegram entregar o webhook (dominio proprio ou tunel como `ngrok`) |

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## Configuracao

Copie o modelo de variaveis de ambiente e preencha com valores reais:

```bash
cp .env.save .env
```

| Variavel | Descricao |
| --- | --- |
| `TOKEN_BOT` | Token do bot, gerado pelo @BotFather. |
| `PROVIDERS` | Nomes dos providers ativos, separados por virgula (ex.: `aliexpress`). Cada nome precisa existir em `providers/__init__.py`. |
| `ALIEXPRESS_CHAVE_APP` | App Key da API de afiliados do AliExpress (necessaria se `aliexpress` estiver em `PROVIDERS`). |
| `ALIEXPRESS_SEGREDO_APP` | App Secret da API de afiliados do AliExpress. |
| `ALIEXPRESS_ID_RASTREAMENTO` | Tracking ID de afiliado usado nas chamadas da API do AliExpress. |
| `ADMIN_USER_IDS` | IDs numericos de usuarios do Telegram (separados por virgula) que veem o menu administrador ao enviar `/start`. Vazio = nenhum administrador. |
| `ADMIN_LINKS_PATH` | Caminho do JSON com botoes extras do menu administrador (padrao: `config/admin_links.json`). |
| `BOT_DISPLAY_NAME` | Nome exibido na mensagem de boas-vindas. |
| `WELCOME_IMAGE_PATH` | Caminho de uma imagem local para a mensagem de boas-vindas (opcional; sem valor, o bot envia so texto). |
| `CART_IMAGE_PATH` | Caminho de uma imagem local para a mensagem de desconto de carrinho (opcional; sem valor, o bot envia so texto). |
| `LINK_TELEGRAM_CHAT` | Link do canal/grupo de chat exibido no menu padrao (opcional). |
| `LINK_TELEGRAM_OFERTAS` | Link do canal de promocoes exibido no menu padrao (opcional). |
| `LINK_YOUTUBE` | Link do canal do YouTube exibido no menu padrao (opcional). |
| `URL_WEBHOOK` | URL publica HTTPS para onde o Telegram deve enviar as atualizacoes (ex.: `https://seudominio.com/webhook`). |
| `PORT` | Porta em que o servidor HTTP local escuta (padrao `8080`). |

O arquivo `.env` nunca deve ser commitado, pois ja esta listado em `.gitignore`. `.env.save` contem apenas valores de exemplo e pode ficar versionado.

Para os botoes extras do menu administrador, copie o modelo e edite:

```bash
cp config/admin_links.example.json config/admin_links.json
```

```json
[
  { "label": "Produto em destaque 1", "url": "https://exemplo.com/produto-1" }
]
```

---

## Como Executar

```bash
source venv/bin/activate
python bot.py
```

Ao iniciar, o script carrega as variaveis de ambiente, ativa os providers listados em `PROVIDERS` (encerra com erro se nenhum ficar ativo), registra os handlers do Telegram e sobe o servidor HTTP (`http.server`) na porta `PORT`, que fica ouvindo `POST /` para receber as atualizacoes do Telegram via webhook.

Para testar localmente sem expor um dominio proprio, exponha a porta com um tunel (`ngrok http 8080`, por exemplo) e use a URL gerada como `URL_WEBHOOK`.

---

## Arquitetura

![Fluxo de uma mensagem, do usuario no Telegram ate a API do provider ativo](docs/architecture.svg)

| Componente | Responsabilidade |
| --- | --- |
| Telegram Bot API | Recebe a mensagem do usuario e entrega a atualizacao ao bot via webhook HTTP. |
| `WebhookHandler` (`bot.py`) | Servidor HTTP que recebe o `POST` do Telegram, valida o JSON e repassa a atualizacao para o `TeleBot`. |
| Handlers (`/start`, mensagem de texto) | Decidem o menu a exibir e extraem o link enviado na mensagem. |
| `encontrar_provider` (`providers/__init__.py`) | Percorre os providers ativos e retorna o primeiro que reconhece a URL recebida. |
| Provider ativo (`AffiliateProvider`) | Cuida de tudo que e especifico da rede de afiliados: normalizacao de link, geracao de link de afiliado e busca de titulo/imagem do produto. |
| Resposta ao usuario | Envia a foto (ou texto, se nao houver imagem) com os links de desconto de volta ao chat de origem. |

Para adicionar uma rede de afiliados nova, copie `providers/example_provider.py`, implemente o contrato de `providers/base.py` e registre a classe em `providers/__init__.py` — nenhuma alteracao em `bot.py` e necessaria.

---

> Documentacao gerada com auxilio de IA.
