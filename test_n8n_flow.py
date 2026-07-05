import django, os, time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from recruitment.models import Resume
from recruitment.ai_service import send_cv_to_n8n

r = Resume.objects.get(pk=1)
r.ai_processed = False
r.score = 0.0
r.save(update_fields=['ai_processed', 'score'])

print(f'Candidato: {r.candidate.username}')
print(f'Texto: {len(r.parsed_text or "")} chars')
print()

result = send_cv_to_n8n(r)
print(f'Enviado para n8n: {result}')
print('A aguardar callback (max 90s)...')
print()

for i in range(18):
    time.sleep(5)
    r.refresh_from_db()
    elapsed = (i + 1) * 5
    print(f'  [{elapsed}s] ai_processed={r.ai_processed}  score={r.score}')
    if r.ai_processed:
        print()
        print('=== CALLBACK RECEBIDO COM SUCESSO ===')
        print(f'Score:      {r.score}')
        print(f'Skills:     {(r.skills or "")[:120]}')
        print(f'Summary:    {(r.summary or "")[:120]}')
        print(f'Experience: {(r.experience or "")[:120]}')
        print(f'Feedback:   {(r.feedback or "")[:120]}')
        break
else:
    print()
    print('TIMEOUT — callback nao chegou em 90s')
