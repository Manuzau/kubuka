import logging
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from .models import Notification

logger = logging.getLogger(__name__)

_STATUS_TEMPLATES = {
    'pre_selected': 'A sua candidatura para "{job}" foi pré-seleccionada! Aguarde contacto do recrutador.',
    'rejected': 'A sua candidatura para "{job}" não foi seleccionada nesta fase. Não desanime - continue a explorar outras vagas.',
    'interview_scheduled': 'Entrevista agendada para a vaga "{job}"{date_part}. Verifique os detalhes na página de candidaturas.',
}

_EMAIL_SUBJECTS = {
    'pre_selected': 'A sua candidatura foi pré-seleccionada - KUBUKA',
    'rejected': 'Actualização da sua candidatura - KUBUKA',
    'interview_scheduled': 'Entrevista agendada - KUBUKA',
}

_STATUS_COLOR = {
    'pre_selected': '#10B981',
    'rejected': '#EF4444',
    'interview_scheduled': '#3B82F6',
}

_STATUS_LABEL = {
    'pre_selected': 'Pré-seleccionado',
    'rejected': 'Não seleccionado',
    'interview_scheduled': 'Entrevista Agendada',
}


def _build_html_email(name, message, status, job_title, base_url):
    color = _STATUS_COLOR.get(status, '#7C3AED')
    label = _STATUS_LABEL.get(status, 'Actualização')
    link = f"{base_url}/my-applications/"
    return f"""<!DOCTYPE html>
<html lang="pt">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0F172A;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0F172A;padding:40px 20px;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#1E293B;border-radius:16px;overflow:hidden;border:1px solid rgba(255,255,255,0.08);">
        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#7C3AED,#4F46E5);padding:28px 36px;text-align:center;">
            <span style="color:#fff;font-size:22px;font-weight:900;letter-spacing:2px;">✦ KUBUKA</span>
            <p style="color:rgba(255,255,255,0.75);font-size:12px;margin:6px 0 0;">Sistema de Pré-Selecção Inteligente de Candidatos</p>
          </td>
        </tr>
        <!-- Badge de estado -->
        <tr>
          <td style="padding:28px 36px 0;text-align:center;">
            <span style="display:inline-block;background:{color};color:#fff;font-size:12px;font-weight:700;padding:6px 18px;border-radius:999px;letter-spacing:1px;text-transform:uppercase;">{label}</span>
          </td>
        </tr>
        <!-- Corpo -->
        <tr>
          <td style="padding:20px 36px 28px;">
            <p style="color:#E2E8F0;font-size:15px;margin:0 0 12px;">Olá <strong>{name}</strong>,</p>
            <p style="color:#CBD5E1;font-size:14px;line-height:1.7;margin:0 0 20px;">{message}</p>
            <p style="color:#94A3B8;font-size:13px;margin:0 0 24px;">Vaga: <strong style="color:#E2E8F0;">{job_title}</strong></p>
            <table cellpadding="0" cellspacing="0"><tr><td style="background:linear-gradient(135deg,#7C3AED,#4F46E5);border-radius:10px;">
              <a href="{link}" style="display:inline-block;color:#fff;font-size:14px;font-weight:700;padding:12px 28px;text-decoration:none;">Ver as minhas candidaturas →</a>
            </td></tr></table>
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="padding:16px 36px;border-top:1px solid rgba(255,255,255,0.06);text-align:center;">
            <p style="color:#475569;font-size:12px;margin:0;">Este é um email automático - não responda a esta mensagem.</p>
            <p style="color:#334155;font-size:11px;margin:6px 0 0;">© 2026 KUBUKA · Luanda, Angola</p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


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
    if not candidate_email:
        return

    subject = _EMAIL_SUBJECTS.get(application.status, 'Actualização da sua candidatura - KUBUKA')
    name = application.candidate.get_full_name() or application.candidate.username
    base_url = getattr(settings, 'DJANGO_BASE_URL', 'http://localhost:8000')

    text_body = (
        f"Olá {name},\n\n"
        f"{message}\n\n"
        f"Aceda a KUBUKA para mais detalhes: {base_url}/my-applications/\n\n"
        f"- Equipa KUBUKA"
    )
    html_body = _build_html_email(name, message, application.status, application.job.title, base_url)

    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[candidate_email],
        )
        email.attach_alternative(html_body, "text/html")
        email.send(fail_silently=True)
        logger.info(f"[notify] Email enviado para {candidate_email} - status={application.status}")
    except Exception as exc:
        logger.warning(f"[notify] Falha ao enviar email para {candidate_email}: {exc}")
