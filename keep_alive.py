import logging
from flask import Flask
from threading import Thread

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def health_check():
    logger.info("Health check request received")
    return {
        "status": "online",
        "service": "Telegram Bot",
        "message": "Bot está operacional"
    }, 200

@app.route('/ping')
def ping():
    """Endpoint simples para testar latência"""
    return "pong"

def run_flask_app():
    """Inicia o servidor Flask em uma thread separada"""
    try:
        logger.info("Iniciando servidor Flask...")
        app.run(
            host='0.0.0.0',
            port=8080,
            debug=False,
            use_reloader=False
        )
    except Exception as e:
        logger.error(f"Erro no servidor Flask: {str(e)}")

def keep_alive():
    """Mantém o bot online criando um webserver"""
    flask_thread = Thread(
        target=run_flask_app,
        daemon=True
    )
    flask_thread.start()
    logger.info("Servidor keep-alive iniciado em segundo plano")