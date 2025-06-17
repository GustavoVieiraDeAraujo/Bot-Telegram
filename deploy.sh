echo ">> Atualizando código do Git"
git pull origin main

echo ">> Parando e removendo container antigo"
docker stop bot-telegram || true
docker rm bot-telegram || true

echo ">> Buildando nova imagem"
docker build -t bot-telegram:latest .

echo ">> Rodando novo container"
docker run -d --name bot-telegram -p 8080:8080 --env-file .env bot-telegram:latest

echo "✅ Deploy finalizado!"