# KUBUKA - imagem de produção (Django + gunicorn + WhiteNoise)
#
# O n8n e o Ollama continuam a correr fora deste container (self-hosted, ver
# README) - esta imagem cobre apenas a aplicação Django.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependências de sistema necessárias para psycopg2 e (opcionalmente) OCR de CVs.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
        tesseract-ocr \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
