import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from .models import Resume, Application
from .notifications import notify_candidate

logger = logging.getLogger(__name__)


def _verify_secret(request):
    """Verifica o header X-Kubuka-Secret."""
    expected = getattr(settings, 'N8N_CALLBACK_SECRET', '') or getattr(settings, 'CALLBACK_SECRET', '')
    received = request.headers.get('X-Kubuka-Secret', '') or request.headers.get('X-Callback-Secret', '')
    if expected and received != expected:
        return False
    return True


@csrf_exempt
@require_POST
def resume_ai_callback(request, resume_id: int):
    """POST /internal/resume/<id>/callback/ — callback legado (compatibilidade)."""
    return _resume_ai_result(request, resume_id)


@csrf_exempt
@require_POST
def resume_ai_result(request, resume_id: int):
    """POST /api/resume/<id>/ai-result/ — callback n8n após análise do CV."""
    return _resume_ai_result(request, resume_id)


def _resume_ai_result(request, resume_id: int):
    if not _verify_secret(request):
        return JsonResponse({'error': 'Token inválido.'}, status=403)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    score = data.get('score')
    if score is None:
        return JsonResponse({'error': "Campo 'score' obrigatório."}, status=400)

    try:
        score = min(max(float(score), 0.0), 100.0)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Score deve ser numérico.'}, status=400)

    try:
        resume = Resume.objects.get(pk=resume_id)
    except Resume.DoesNotExist:
        return JsonResponse({'error': f'Resume {resume_id} não encontrado.'}, status=404)

    resume.score = round(score, 1)
    resume.skills = data.get('skills', resume.skills or '')
    resume.summary = data.get('summary', resume.summary or '')
    resume.experience = data.get('experience', resume.experience or '')
    resume.education = data.get('education', resume.education or '')
    resume.languages = data.get('languages', resume.languages or '')
    resume.feedback = data.get('feedback', resume.feedback or '')
    resume.ai_processed = True
    resume.save(update_fields=[
        'score', 'skills', 'summary', 'experience',
        'education', 'languages', 'feedback', 'ai_processed'
    ])

    logger.info(f"[callback] Resume {resume_id} actualizado — score={resume.score}")
    return JsonResponse({'success': True, 'resume_id': resume_id, 'score': resume.score})


@csrf_exempt
@require_POST
def application_score_result(request, application_id: int):
    """POST /api/application/<id>/score-result/ — callback n8n com score de candidatura."""
    if not _verify_secret(request):
        return JsonResponse({'error': 'Token inválido.'}, status=403)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    score = data.get('similarity_score')
    if score is None:
        return JsonResponse({'error': "Campo 'similarity_score' obrigatório."}, status=400)

    try:
        score = min(max(float(score), 0.0), 100.0)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Score deve ser numérico.'}, status=400)

    try:
        application = Application.objects.get(pk=application_id)
    except Application.DoesNotExist:
        return JsonResponse({'error': f'Application {application_id} não encontrada.'}, status=404)

    application.similarity_score = round(score, 1)
    application.match_feedback = data.get('match_feedback', '')
    update_fields = ['similarity_score', 'match_feedback']

    job = application.job
    auto_rejected = False
    if job.min_score_required > 0 and application.similarity_score < job.min_score_required:
        application.status = 'rejected'
        application.match_feedback = (application.match_feedback or '') + (
            f'\n\n[Triagem automática] Score {application.similarity_score}% abaixo do mínimo '
            f'exigido ({job.min_score_required}%) para esta vaga.'
        )
        update_fields.extend(['status', 'updated_at'])
        auto_rejected = True

    application.save(update_fields=update_fields)

    if auto_rejected:
        notify_candidate(application)

    logger.info(
        f"[callback] Application {application_id} actualizada — score={application.similarity_score}"
        + (' (auto-rejeitada)' if auto_rejected else '')
    )
    return JsonResponse({'success': True, 'application_id': application_id, 'score': application.similarity_score, 'auto_rejected': auto_rejected})


@csrf_exempt
@require_POST
def application_update_status(request, application_id: int):
    """POST /api/application/<id>/update-status/ — recrutador pré-selecciona ou rejeita."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Autenticação necessária.'}, status=401)
    if not (request.user.is_recruiter or request.user.is_staff or request.user.is_admin):
        return JsonResponse({'error': 'Permissão negada.'}, status=403)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    from django.utils.dateparse import parse_datetime
    new_status = data.get('status')
    valid = [s[0] for s in Application.STATUS_CHOICES]
    if new_status not in valid:
        return JsonResponse({'error': f'Status inválido. Valores aceites: {valid}'}, status=400)

    try:
        application = Application.objects.get(pk=application_id)
    except Application.DoesNotExist:
        return JsonResponse({'error': f'Application {application_id} não encontrada.'}, status=404)

    update_fields = ['status', 'updated_at']
    application.status = new_status

    if new_status == 'interview_scheduled':
        interview_date_str = data.get('interview_date')
        if interview_date_str:
            interview_date = parse_datetime(interview_date_str)
            if interview_date:
                application.interview_date = interview_date
                update_fields.append('interview_date')
        application.candidate_availability_enabled = application.job.allow_candidate_unavailability
        update_fields.append('candidate_availability_enabled')

    recruiter_notes = data.get('recruiter_notes')
    if recruiter_notes is not None:
        application.recruiter_notes = recruiter_notes
        update_fields.append('recruiter_notes')

    application.save(update_fields=update_fields)
    notify_candidate(application)
    return JsonResponse({'success': True, 'application_id': application_id, 'status': application.status})
