from .models import Notification

_STATUS_TEMPLATES = {
    'pre_selected': 'A sua candidatura para "{job}" foi pré-seleccionada! Aguarde contacto do recrutador.',
    'rejected': 'A sua candidatura para "{job}" não foi seleccionada nesta fase. Não desanime — continue a explorar outras vagas.',
    'interview_scheduled': 'Entrevista agendada para a vaga "{job}"{date_part}. Verifique os detalhes na página de candidaturas.',
}


def notify_candidate(application):
    """Creates a Notification for the candidate whenever the recruiter changes the application status."""
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
