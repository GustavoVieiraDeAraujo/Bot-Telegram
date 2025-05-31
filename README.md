# Bot Telegram

---

## ⚙️ Pré-requisitos

Antes de iniciar o projeto, verifique se você possui os seguintes requisitos:

- **pip** (gerenciador de pacotes do Python).
- **Python 3.7 ou superior** instalado no sistema.
- Conta no **Telegram** com um bot criado via [@BotFather](https://t.me/BotFather).
- Uma conta de **afiliado do AliExpress** com as seguintes credenciais:
  - `CHAVE_APP` (App Key)
  - `SEGREDO_APP` (App Secret)
  - `ID_RASTREAMENTO` (Tracking ID de afiliado)

### 🔐 Variáveis de ambiente necessárias

Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```env
TOKEN_BOT=seu_token_do_telegram
LINK_CANAL=https://t.me/seu_canal
CHAVE_APP=sua_chave_da_api_aliexpress
SEGREDO_APP=seu_segredo_da_api_aliexpress
ID_RASTREAMENTO=seu_id_rastreamento_afiliado
LINK_COMPARTILHAR_GANHAR=https://s.click.aliexpress.com/seulink
```

---

## 📦 Instalação

Siga os passos abaixo para instalar e executar o projeto em seu sistema operacional.

### 🐧 Ubuntu/Linux

1. **Instale o Python e o Pip**

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

2. **Clone o repositório:**

```bash
git clone https://github.com/seu-usuario/seu-repositorio.git
cd seu-repositorio
```

3. **Crie e ative o ambiente virtual:**

```bash
python3 -m venv venv
source venv/bin/activate
```

4. **Instale as dependências:**

```bash
pip install -r requirements.txt
```

5. **Configure o arquivo `.env`:**

Crie o arquivo `.env` com as variáveis listadas na seção [Pré-requisitos](#pré-requisitos).

6. **Execute o bot:**

```bash
python bot.py
```

---

### 🪟 Windows

1. **Instale o Python:**

- Acesse: [https://www.python.org/downloads](https://www.python.org/downloads)
- Marque a opção **"Add Python to PATH"** durante a instalação.

2. **Clone o repositório:**

Abra o terminal (CMD, PowerShell ou Git Bash) e execute:

```bash
git clone https://github.com/seu-usuario/seu-repositorio.git
cd seu-repositorio
```

3. **Crie e ative o ambiente virtual:**

```bash
python -m venv venv
venv\Scripts\activate
```

4. **Instale as dependências:**

```bash
pip install -r requirements.txt
```

5. **Configure o arquivo `.env`:**

Crie o arquivo `.env` com as variáveis listadas na seção [Pré-requisitos](#pré-requisitos).

6. **Execute o bot:**

```bash
python bot.py
```

---

> ✅ O bot estará em execução e pronto para receber comandos no Telegram.