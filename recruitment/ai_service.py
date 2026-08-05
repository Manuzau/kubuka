import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send_cv_to_n8n(resume):
    cv_text = resume.parsed_text or ''
    if not cv_text.strip():
        logger.warning(f'Resume {resume.pk} sem texto extraído - análise de IA ignorada.')
        return False

    callback_url = f"{settings.DJANGO_BASE_URL}/api/resume/{resume.pk}/ai-result/"

    try:
        resp = requests.post(
            settings.N8N_WEBHOOK_CV_URL,
            json={
                'resume_id': resume.pk,
                'cv_text': cv_text[:6000],
                'callback_url': callback_url,
            },
            timeout=30,
        )
        resp.raise_for_status()
        logger.info(f'Resume {resume.pk} enviado para n8n - a aguardar callback.')
        return True
    except requests.RequestException as exc:
        logger.error(f'Erro ao contactar n8n para Resume {resume.pk}: {exc}')
        return False


def send_application_for_scoring(application):
    resume = getattr(application.candidate, 'resume', None)

    if application.cv_parsed_text:
        skills = application.cv_parsed_text
        summary = ''
        experience = ''
    else:
        skills = resume.skills if resume else ''
        summary = resume.summary if resume else ''
        experience = resume.experience if resume else ''

    callback_url = f"{settings.DJANGO_BASE_URL}/api/application/{application.pk}/score-result/"

    try:
        application.awaiting_score = True
        application.save(update_fields=['awaiting_score'])

        resp = requests.post(
            settings.N8N_WEBHOOK_SCORE_URL,
            json={
                'application_id': application.pk,
                'candidate_skills': skills,
                'candidate_summary': summary,
                'candidate_experience': experience,
                'job_title': application.job.title,
                'job_requirements': application.job.requirements,
                'callback_url': callback_url,
            },
            timeout=30,
        )
        resp.raise_for_status()
        logger.info(f'Application {application.pk} enviada para n8n.')
        return True
    except requests.RequestException as exc:
        logger.error(f'Erro ao contactar n8n para Application {application.pk}: {exc}')
        application.awaiting_score = False
        application.save(update_fields=['awaiting_score'])
        return False
