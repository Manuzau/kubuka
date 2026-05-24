import logging
from django.core.mail import send_mail
from django.conf import settings
from .models import Notification

logger = logging.getLogger(__name__)

_STATUS_TEMPLATES = {
    'pre_selected': 'A sua candidatura para "{job}" foi pré-seleccionada! Aguarde contacto do recrutador.',
    'rejected': 'A sua candidatura para "{job}" não foi seleccionada nesta fase. Não desanime — continue a explorar outras vagas.',
    'interview_scheduled': 'Entrevista agendada para a vaga "{job}"{date_part}. Verifique os detalhes na página de candidaturas.',
}

_EMAIL_SUBJECTS = {
    'pre_selected': 'A sua candidatura foi pré-seleccionada — KUBUKA',
    'rejected': 'Actualização da sua candidatura — KUBUKA',
    'interview_scheduled': 'Entrevista agendada — KUBUKA',
}


def notify_candidate(application):
    """Cria notificação na BD e envia email ao candidato quando o estado muda."""
    template = _STATUS_TEMPLATES.get(application.status)
    if not template:
        return

    date_part = ''
    if application.status == 'interview_scheduled' and application.interview_date:
        date_part = ' em ' + application.interview_date.strftime('%d/%m/%Y às %H:%M')

    message = template.format(job=application.job.title, date_part=date_part)

    Notification.objects.create(
        user=application.candidate,
        application=application,
        message=message,
    )

    candidate_email = application.candidate.email
    if candidate_email:
        subject = _EMAIL_SUBJECTS.get(application.status, 'Actualização da sua candidatura — KUBUKA')
        email_body = (
            f"Olá {application.candidate.get_full_name() or application.candidate.username},\n\n"
            f"{message}\n\n"
            f"Aceda a KUBUKA para mais detalhes: {getattr(settings, 'DJANGO_BASE_URL', 'http://localhost:8000')}/my-applications/\n\n"
            f"— Equipa KUBUKA"
        )
        try:
            send_mail(
                subject=subject,
                message=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[candidate_email],
                fail_silently=True,
            )
            logger.info(f"[notify] Email enviado para {candidate_email} — status={application.status}")
        except Exception as exc:
            logger.warning(f"[notify] Falha ao enviar email para {candidate_email}: {exc}")
