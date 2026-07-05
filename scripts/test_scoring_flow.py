import django, os, time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from recruitment.models import User, Job, Application, Resume
from recruitment.ai_service import send_application_for_scoring

# Procurar candidato com resume processado
resume = Resume.objects.filter(ai_processed=True).select_related('candidate').first()
if not resume:
    print('ERRO: Nenhum resume ai_processed=True encontrado. Faz primeiro upload de um CV.')
    exit(1)

candidate = resume.candidate

# Procurar ou criar uma vaga de teste
recruiter = User.objects.filter(is_recruiter=True).first()
if not recruiter:
    recruiter = User.objects.filter(is_staff=True).first()

job, created = Job.objects.get_or_create(
    title='Engenheiro de Software (Teste)',
    defaults={
        'company': 'Kubuka Teste',
        'description': 'Posicao de teste para validar o scoring de candidaturas.',
        'requirements': 'Python, Django, SQL, trabalho em equipa, resolucao de problemas.',
        'location': 'Luanda',
        'is_active': True,
        'created_by': recruiter,
    }
)
if created:
    print(f'Vaga criada: {job.title}')
else:
    print(f'Vaga existente: {job.title}')

# Remover candidatura anterior se existir (para novo teste)
Application.objects.filter(candidate=candidate, job=job).delete()

app = Application.objects.create(candidate=candidate, job=job, status='pending')
print(f'\nCandidato: {candidate.username}')
print(f'Skills no resume: {(resume.skills or "")[:100]}')
print(f'Application pk={app.pk}')
print()

ok = send_application_for_scoring(app)
print(f'Enviado para n8n: {ok}')
print('A aguardar callback do scoring (max 120s)...')
print()

for i in range(24):
    time.sleep(5)
    app.refresh_from_db()
    elapsed = (i + 1) * 5
    print(f'  [{elapsed}s] awaiting_score={app.awaiting_score}  similarity_score={app.similarity_score}  status={app.status}')
    if not app.awaiting_score and app.similarity_score > 0:
        print()
        print('=== SCORING RECEBIDO COM SUCESSO ===')
        print(f'Similarity Score:  {app.similarity_score}%')
        print(f'Match Feedback:    {(app.match_feedback or "")[:200]}')
        print(f'Status:            {app.get_status_display()}')
        break
else:
    print()
    print('TIMEOUT — callback de scoring nao chegou em 120s')
    print(f'Estado final: awaiting_score={app.awaiting_score}  score={app.similarity_score}')
