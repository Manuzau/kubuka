import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send_cv_to_n8n(resume):
    """Envia o CV para o n8n para análise pelo Ollama."""
    webhook_url = getattr(settings, 'N8N_WEBHOOK_CV_URL', '')
    if not webhook_url:
        logger.warning("[ai_service] N8N_WEBHOOK_CV_URL não configurado — análise de CV ignorada.")
        return False

    callback_url = (
        getattr(settings, 'DJANGO_BASE_URL', 'http://localhost:8000')
        + f'/api/resume/{resume.pk}/ai-result/'
    )

    payload = {
        'resume_id': resume.pk,
        'cv_text': resume.parsed_text or '',
        'callback_url': callback_url,
    }
    headers = {'X-Kubuka-Secret': getattr(settings, 'N8N_CALLBACK_SECRET', '')}

    try:
        response = requests.post(webhook_url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        logger.info(f"[ai_service] CV {resume.pk} enviado ao n8n — status {response.status_code}")
        return True
    except requests.RequestException as exc:
        logger.error(f"[ai_service] Falha ao enviar CV {resume.pk} ao n8n: {exc}")
        return False


def send_application_for_scoring(application):
    """Envia candidatura para o n8n calcular o score de correspondência."""
    webhook_url = getattr(settings, 'N8N_WEBHOOK_SCORE_URL', '')
    if not webhook_url:
        logger.warning("[ai_service] N8N_WEBHOOK_SCORE_URL não configurado — scoring ignorado.")
        return False

    callback_url = (
        getattr(settings, 'DJANGO_BASE_URL', 'http://localhost:8000')
        + f'/api/application/{application.pk}/score-result/'
    )

    resume = getattr(application.candidate, 'resume', None)

    # Usar CV específico da candidatura se disponível; caso contrário usa o CV do perfil
    if application.cv_parsed_text:
        candidate_skills = application.cv_parsed_text
        candidate_summary = ''
        candidate_experience = ''
        cv_source = 'specific'
    else:
        candidate_skills = resume.skills if resume else ''
        candidate_summary = resume.summary if resume else ''
        candidate_experience = resume.experience if resume else ''
        cv_source = 'profile'

    payload = {
        'application_id': application.pk,
        'candidate_skills': candidate_skills,
        'candidate_summary': candidate_summary,
        'candidate_experience': candidate_experience,
        'job_title': application.job.title,
        'job_requirements': application.job.requirements,
        'callback_url': callback_url,
        'cv_source': cv_source,
    }
    headers = {'X-Kubuka-Secret': getattr(settings, 'N8N_CALLBACK_SECRET', '')}

    try:
        response = requests.post(webhook_url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        # Marca a candidatura como aguardando resultado — só agora o callback é autorizado
        application.awaiting_score = True
        application.save(update_fields=['awaiting_score'])
        logger.info(f"[ai_service] Application {application.pk} enviada ao n8n — status {response.status_code}")
        return True
    except requests.RequestException as exc:
        logger.error(f"[ai_service] Falha ao enviar application {application.pk} ao n8n: {exc}")
        return False
