"""
n8n_client.py — Envia o CV extraído para o n8n via webhook.

Fluxo:
    upload_resume (views.py)
        → extract_text_from_pdf (cv_processor.py)
        → send_cv_to_n8n  ← este módulo
            → n8n processa
            → Ollama analisa
        → /internal/resume/<id>/callback/  (callback_views.py)
            → BD actualizada com score + skills + feedback

Configuração necessária no .env:
    N8N_WEBHOOK_URL=http://localhost:5678/webhook/cv-analysis
    N8N_SECRET_TOKEN=token-secreto-partilhado
"""

import threading
import requests
from django.conf import settings


def send_cv_to_n8n(resume_id: int, cv_text: str) -> None:
    """
    Envia o texto do CV ao n8n de forma assíncrona (não bloqueia o pedido HTTP).

    Parâmetros:
        resume_id  — ID do objecto Resume na base de dados.
        cv_text    — Texto extraído do PDF pelo cv_processor.
    """
    thread = threading.Thread(
        target=_post_webhook,
        args=(resume_id, cv_text),
        daemon=True,  # termina com o processo principal
    )
    thread.start()


def _post_webhook(resume_id: int, cv_text: str) -> None:
    """Chamada bloqueante que corre numa thread separada."""
    url = getattr(settings, 'N8N_WEBHOOK_URL', None)
    token = getattr(settings, 'N8N_SECRET_TOKEN', '')

    if not url:
        print("[n8n_client] N8N_WEBHOOK_URL não definido no .env — ignorando envio.")
        return

    payload = {
        "resume_id": resume_id,
        "cv_text": cv_text,
    }
    cabecalhos = {
        "Content-Type": "application/json",
        "X-N8N-Secret": token,
    }

    try:
        resposta = requests.post(url, json=payload, headers=cabecalhos, timeout=30)
        resposta.raise_for_status()
        print(f"[n8n_client] Webhook enviado com sucesso para resume_id={resume_id}.")
    except requests.exceptions.ConnectionError:
        print(f"[n8n_client] Falha de ligação ao n8n ({url}). O n8n está em execução?")
    except requests.exceptions.Timeout:
        print(f"[n8n_client] Timeout ao contactar o n8n para resume_id={resume_id}.")
    except requests.exceptions.HTTPError as erro:
        print(f"[n8n_client] Erro HTTP do n8n: {erro}")
    except Exception as erro:
        print(f"[n8n_client] Erro inesperado: {erro}")