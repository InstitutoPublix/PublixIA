FROM python:3.11-slim

# Não escrever .pyc e não bufferizar stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Pasta onde o app vai ficar dentro do container
WORKDIR /app

# Dependências de sistema básicas (caso alguma lib precise compilar)
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Instala as libs do Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante dos arquivos do projeto para dentro do container
COPY . .

# Porta padrão do Streamlit
EXPOSE 8501

# IMPORTANTE: usar o nome REAL do arquivo do app
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
