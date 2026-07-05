import json
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

OLLAMA_URL = 'http://127.0.0.1:11434/api/generate'
OLLAMA_MODEL = 'llama3.2:1b'
OLLAMA_TIMEOUT = 180  # seconds — 1b model is fast (~15s), 180s is safe headroom


def _call_ollama(prompt: str) -> dict:
    """Call Ollama directly and return the parsed JSON response dict."""
    payload = {
        'model': OLLAMA_MODEL,
        'stream': False,       # boolean — never a string
        'format': 'json',
        'prompt': prompt,
    }
    resp = requests.post(
        OLLAMA_URL,
        json=payload,           # requests serialises booleans correctly
        timeout=OLLAMA_TIMEOUT,
    )
    resp.raise_for_status()
    raw = resp.json().get('response', '{}')
    cleaned = raw.replace('```json', '').replace('```', '').strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning('[ai_service] Ollama response is not valid JSON — using defaults')
        return {}


def _to_str(val) -> str:
    if val is None:
        return ''
    if isinstance(val, str):
        return val.strip()
    if isinstance(val, list):
        return ', '.join(str(i) for i in val)
    if isinstance(val, dict):
        return ' | '.join(str(v) for v in val.values() if v)
    return str(val)


# ─────────────────────────────────────────────────────────────────────────────
# CV Analysis
# ─────────────────────────────────────────────────────────────────────────────

def _analyse_cv(cv_text: str) -> dict:
    prompt = (
        'Analisa o seguinte curriculo e responde APENAS com JSON valido com estes campos: '
        'score (inteiro 0-100), skills (lista de strings), summary (string), '
        'experience (string), education (string), languages (string), feedback (string).\n\n'
        'Curriculo:\n' + cv_text[:6000]
    )
    data = _call_ollama(prompt)
    return {
        'score':      min(100, max(0, float(data.get('score') or 50))),
        'skills':     _to_str(data.get('skills'))     or 'Nao identificadas',
        'summary':    _to_str(data.get('summary'))    or 'Resumo nao disponivel',
        'experience': _to_str(data.get('experience')) or 'Nao especificada',
        'education':  _to_str(data.get('education'))  or 'Nao especificada',
        'languages':  _to_str(data.get('languages'))  or 'Nao identificados',
        'feedback':   _to_str(data.get('feedback'))   or 'Analise concluida.',
    }


def send_cv_to_n8n(resume):
    """Analyse resume with Ollama and update the Resume record directly.

    Named 'send_cv_to_n8n' to keep all existing callers unchanged.
    If Ollama is unreachable the system continues in degraded mode.
    """
    cv_text = resume.parsed_text or ''
    if not cv_text.strip():
        logger.warning(f'[ai_service] Resume {resume.pk} has no parsed text — skipping AI analysis.')
        return False

    try:
        result = _analyse_cv(cv_text)
        resume.score      = round(result['score'], 1)
        resume.skills     = result['skills']
        resume.summary    = result['summary']
        resume.experience = result['experience']
        resume.education  = result['education']
        resume.languages  = result['languages']
        resume.feedback   = result['feedback']
        resume.ai_processed = True
        resume.save(update_fields=[
            'score', 'skills', 'summary', 'experience',
            'education', 'languages', 'feedback', 'ai_processed',
        ])
        logger.info(f'[ai_service] Resume {resume.pk} analisado — score={resume.score}')
        return True
    except requests.RequestException as exc:
        logger.error(f'[ai_service] Ollama indisponivel para Resume {resume.pk}: {exc}')
        return False
    except Exception as exc:
        logger.error(f'[ai_service] Erro inesperado ao analisar Resume {resume.pk}: {exc}')
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Job Scoring
# ─────────────────────────────────────────────────────────────────────────────

def _score_application(candidate_skills, candidate_summary, candidate_experience,
                       job_title, job_requirements) -> dict:
    prompt = (
        'Compara o candidato com a vaga. Responde APENAS com JSON valido com dois campos: '
        'similarity_score (inteiro 0-100) e match_feedback (string).\n\n'
        f'Candidato — Skills: {candidate_skills[:2000]} | '
        f'Resumo: {candidate_summary[:1000]} | '
        f'Experiencia: {candidate_experience[:2000]}\n'
        f'Vaga: {job_title} | Requisitos: {job_requirements[:3000]}'
    )
    data = _call_ollama(prompt)
    return {
        'similarity_score': min(100, max(0, float(data.get('similarity_score') or 0))),
        'match_feedback':   _to_str(data.get('match_feedback')) or 'Analise nao disponivel.',
    }


def send_application_for_scoring(application):
    """Score application with Ollama and update the Application record directly.

    Named 'send_application_for_scoring' to keep all existing callers unchanged.
    """
    resume = getattr(application.candidate, 'resume', None)

    if application.cv_parsed_text:
        candidate_skills   = application.cv_parsed_text
        candidate_summary  = ''
        candidate_experience = ''
    else:
        candidate_skills   = resume.skills     if resume else ''
        candidate_summary  = resume.summary    if resume else ''
        candidate_experience = resume.experience if resume else ''

    try:
        application.awaiting_score = True
        application.save(update_fields=['awaiting_score'])

        result = _score_application(
            candidate_skills, candidate_summary, candidate_experience,
            application.job.title, application.job.requirements,
        )

        application.similarity_score = round(result['similarity_score'], 1)
        application.match_feedback   = result['match_feedback']
        application.awaiting_score   = False
        update_fields = ['similarity_score', 'match_feedback', 'awaiting_score']

        job = application.job
        auto_rejected = False
        if job.min_score_required > 0 and application.similarity_score < job.min_score_required:
            application.status = 'rejected'
            application.match_feedback += (
                f'\n\n[Triagem automática] Score {application.similarity_score}% abaixo do '
                f'mínimo exigido ({job.min_score_required}%) para esta vaga.'
            )
            update_fields.extend(['status', 'updated_at'])
            auto_rejected = True

        application.save(update_fields=update_fields)

        from .notifications import notify_candidate
        if auto_rejected:
            notify_candidate(application)

        logger.info(
            f'[ai_service] Application {application.pk} scored — '
            f'score={application.similarity_score}'
            + (' (auto-rejeitada)' if auto_rejected else '')
        )
        return True
    except requests.RequestException as exc:
        logger.error(f'[ai_service] Ollama indisponivel para Application {application.pk}: {exc}')
        application.awaiting_score = False
        application.save(update_fields=['awaiting_score'])
        return False
    except Exception as exc:
        logger.error(f'[ai_service] Erro inesperado ao pontuar Application {application.pk}: {exc}')
        return False
