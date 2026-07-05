"""Teste end-to-end: analise de CV + scoring de candidatura.

Fluxo:
  1. Reset do Resume pk=1 (candidata Iracelma)
  2. Envia CV ao n8n -> aguarda callback com score/skills/etc.
  3. Cria Application para uma vaga -> aguarda callback com similarity_score
  4. Mostra o resultado final
"""
import django, os, time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from recruitment.models import Resume, Job, Application, User
from recruitment.ai_service import send_cv_to_n8n, send_application_for_scoring


def wait_for(condition_fn, timeout, label, poll=5):
    for i in range(timeout // poll):
        time.sleep(poll)
        elapsed = (i + 1) * poll
        ok, extra = condition_fn()
        marker = 'OK' if ok else '...'
        print(f'  [{elapsed:>3}s] {label} {marker}  {extra}')
        if ok:
            return True
    return False


print('=' * 70)
print(' TESTE END-TO-END: CV + Candidatura')
print('=' * 70)
print()

# --- 1. Preparar candidato e Resume ---
resume = Resume.objects.get(pk=1)
candidate = resume.candidate
print(f'Candidato: {candidate.username}')
print(f'CV: {len(resume.parsed_text or "")} chars extraidos')
print()

# Reset do Resume para simular novo processamento
resume.ai_processed = False
resume.score = 0.0
resume.skills = ''
resume.summary = ''
resume.experience = ''
resume.education = ''
resume.languages = ''
resume.feedback = ''
resume.save()
print('Resume resetado (ai_processed=False)')

# --- 2. FASE 1: Analise de CV ---
print()
print('-' * 70)
print(' FASE 1 - Analise de CV')
print('-' * 70)
ok = send_cv_to_n8n(resume)
print(f'CV enviado para n8n: {ok}')
print('A aguardar callback do n8n (max 6 min)...')
print()

def cv_ready():
    resume.refresh_from_db()
    return resume.ai_processed, f'ai_processed={resume.ai_processed} score={resume.score}'

if not wait_for(cv_ready, timeout=360, label='CV', poll=10):
    print()
    print('FALHA: callback do CV nao chegou em 6min')
    exit(1)

print()
print('CV ANALISADO:')
print(f'  Score:      {resume.score}%')
print(f'  Skills:     {(resume.skills or "")[:200]}')
print(f'  Summary:    {(resume.summary or "")[:200]}')
print(f'  Experience: {(resume.experience or "")[:200]}')
print(f'  Education:  {(resume.education or "")[:200]}')
print(f'  Languages:  {(resume.languages or "")[:200]}')
print(f'  Feedback:   {(resume.feedback or "")[:200]}')

# --- 3. FASE 2: Candidatura e Scoring ---
print()
print('-' * 70)
print(' FASE 2 - Candidatura e Scoring')
print('-' * 70)
job = Job.objects.filter(title__icontains='Engenheiro de Software').first()
if not job:
    print('FALHA: vaga de teste nao encontrada')
    exit(1)
print(f'Vaga: {job.title} @ {job.company}')
print(f'Requisitos: {job.requirements[:200]}')

# Remove candidatura anterior para novo teste
Application.objects.filter(candidate=candidate, job=job).delete()
app = Application.objects.create(candidate=candidate, job=job, status='pending')
print(f'Application pk={app.pk} criada')
print()

ok = send_application_for_scoring(app)
print(f'Application enviada para n8n: {ok}')
print('A aguardar callback do scoring (max 4 min)...')
print()

def score_ready():
    app.refresh_from_db()
    return (not app.awaiting_score) and app.similarity_score > 0, \
        f'awaiting={app.awaiting_score} score={app.similarity_score}'

if not wait_for(score_ready, timeout=240, label='SCORE', poll=10):
    print()
    print('FALHA: callback do scoring nao chegou em 4min')
    exit(1)

print()
print('CANDIDATURA PONTUADA:')
print(f'  Similarity Score: {app.similarity_score}%')
print(f'  Match Feedback:   {(app.match_feedback or "")[:400]}')
print(f'  Status:           {app.get_status_display()}')

# --- 4. Resumo ---
print()
print('=' * 70)
print(' RESUMO FINAL')
print('=' * 70)
print(f'  Candidato:                    {candidate.username}')
print(f'  Score do CV (qualidade):      {resume.score}%')
print(f'  Score de correspondencia:     {app.similarity_score}%')
print(f'  Vaga:                         {job.title}')
print(f'  Status final da candidatura:  {app.get_status_display()}')
print()
print('SUCESSO - fluxo end-to-end completo.')
