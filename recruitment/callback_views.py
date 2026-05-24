import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from .models import Resume, Application

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
        data = json.loads(request.body)
    except json.JSONDecodeError:
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
        data = json.loads(request.body)
    except json.JSONDecodeError:
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
    application.save(update_fields=['similarity_score', 'match_feedback'])

    logger.info(f"[callback] Application {application_id} actualizada — score={application.similarity_score}")
    return JsonResponse({'success': True, 'application_id': application_id, 'score': application.similarity_score})


@csrf_exempt
@require_POST
def application_update_status(request, application_id: int):
    """POST /api/application/<id>/update-status/ — recrutador pré-selecciona ou rejeita."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Autenticação necessária.'}, status=401)
    if not (request.user.is_recruiter or request.user.is_staff or request.user.is_admin):
        return JsonResponse({'error': 'Permissão negada.'}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    new_status = data.get('status')
    valid = [s[0] for s in Application.STATUS_CHOICES]
    if new_status not in valid:
        return JsonResponse({'error': f'Status inválido. Valores aceites: {valid}'}, status=400)

    try:
        application = Application.objects.get(pk=application_id)
    except Application.DoesNotExist:
        return JsonResponse({'error': f'Application {application_id} não encontrada.'}, status=404)

    application.status = new_status
    application.save(update_fields=['status'])
    return JsonResponse({'success': True, 'application_id': application_id, 'status': application.status})
