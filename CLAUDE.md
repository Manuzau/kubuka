# CLAUDE.md — KUBUKA
> Ficheiro de contexto para o Claude Code. Lê este ficheiro antes de qualquer tarefa.

---

## 1. O Que é Este Projecto

**KUBUKA** é um sistema web de pré-selecção inteligente de candidatos para empresas angolanas.  
Trabalho de Fim de Curso (TFC) — Licenciatura em Informática.

**Stack principal:**
- Backend: Django 5.x + Django REST Framework
- Frontend: Django Templates + Tailwind CSS (CDN) + Flowbite
- Extracção de CV: pdfplumber + pytesseract (OCR) + pdf2image
- Automação: n8n (self-hosted, porta 5678)
- IA: Ollama com modelo llama3.2 (local, porta 11434)
- Base de dados: SQLite (desenvolvimento)
- Configuração: django-environ (.env)

---

## 2. Estrutura de Ficheiros

```
kubuka/
├── core/
│   ├── settings.py          # Configurações Django (lê .env)
│   ├── urls.py              # Inclui recruitment.urls
│   └── wsgi.py
├── recruitment/
│   ├── models.py            # User, Resume, Job, Application (a criar)
│   ├── views.py             # Views HTML (candidatos, recrutadores)
│   ├── api_views.py         # Endpoints REST (DRF)
│   ├── urls.py              # Todas as rotas
│   ├── forms.py             # Formulários Django
│   ├── serializers.py       # Serializadores DRF
│   ├── cv_processor.py      # Extracção de texto PDF (pdfplumber + OCR)
│   ├── ai_service.py        # [A CRIAR] Comunicação com n8n/Ollama
│   ├── admin.py             # Registo no Django Admin
│   ├── tests.py             # Testes automatizados
│   ├── migrations/          # Migrations da BD
│   └── templates/
│       └── recruitment/
│           ├── base.html
│           ├── index.html
│           ├── home_authenticated.html
│           ├── login.html
│           ├── signup.html
│           ├── upload.html
│           ├── upload_success.html
│           ├── resume_detail.html
│           ├── resume_edit.html
│           ├── dashboard.html       # Painel do recrutador
│           ├── job_list.html
│           ├── job_form.html        # [A CRIAR]
│           └── job_manage.html      # [A CRIAR]
├── media/
│   └── resumes/             # Ficheiros PDF submetidos
├── .env                     # Variáveis de ambiente (não commitar)
├── .env.example
├── requirements.txt
└── manage.py
```

---

## 3. Modelos de Dados

### 3.1 Modelos Actuais

```python
# User — modelo customizado (AbstractUser)
class User(AbstractUser):
    is_candidate = models.BooleanField(default=False)
    is_recruiter  = models.BooleanField(default=False)  # [ADICIONAR]
    is_admin      = models.BooleanField(default=False)
    # is_staff herdado do AbstractUser = Administrador Django

# Resume — CV do candidato (1 por candidato)
class Resume(models.Model):
    candidate    = models.OneToOneField(User, ...)
    file         = models.FileField(upload_to='resumes/')
    parsed_text  = models.TextField(...)      # Texto bruto extraído
    summary      = models.TextField(...)      # Gerado pela IA
    skills       = models.TextField(...)      # Lista de competências (IA)
    experience   = models.TextField(...)      # Experiência (IA)
    education    = models.TextField(...)      # Formação (IA)
    languages    = models.TextField(...)      # Idiomas (IA)
    score        = models.FloatField(...)     # Qualidade geral do CV (IA)
    feedback     = models.TextField(...)      # Análise geral (IA)
    ai_processed = models.BooleanField(...)   # [ADICIONAR]
    created_at   = models.DateTimeField(...)

# Job — vaga de emprego
class Job(models.Model):
    title        = models.CharField(...)
    company      = models.CharField(...)
    description  = models.TextField(...)
    requirements = models.TextField(...)
    location     = models.CharField(...)
    salary_range = models.CharField(...)
    is_active    = models.BooleanField(...)   # [ADICIONAR]
    created_by   = models.ForeignKey(User)    # [ADICIONAR]
    created_at   = models.DateTimeField(...)
    applicants   = models.ManyToManyField(...)  # Substituir por Application
```

### 3.2 Novo Modelo a Criar

```python
# Application — candidatura de um candidato a uma vaga específica
class Application(models.Model):
    STATUS_CHOICES = [
        ('pending',       'Pendente'),
        ('pre_selected',  'Pré-seleccionado'),
        ('rejected',      'Rejeitado'),
    ]
    candidate         = models.ForeignKey(User, related_name='applications', ...)
    job               = models.ForeignKey(Job,  related_name='applications', ...)
    similarity_score  = models.FloatField(default=0.0)   # Score candidato x vaga
    match_feedback    = models.TextField(blank=True, null=True)
    status            = models.CharField(choices=STATUS_CHOICES, default='pending')
    applied_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('candidate', 'job')  # 1 candidatura por vaga
```

---

## 4. Os Três Perfis (Roles)

| Role | Campo no modelo | Acesso |
|---|---|---|
| **Candidato** | `is_candidate=True` | Gere o próprio CV, explora vagas, submete candidaturas, vê feedback geral do CV |
| **Recrutador** | `is_recruiter=True` | Cria/edita/publica vagas, vê candidatos das suas vagas com score de correspondência, pré-selecciona |
| **Administrador** | `is_staff=True` ou `is_admin=True` | Acesso total, inclui Django Admin |

**Regra de verificação nas views:**
```python
# Candidato
if not request.user.is_candidate:
    return redirect('home')

# Recrutador
if not (request.user.is_recruiter or request.user.is_staff):
    return redirect('home')

# Admin
if not (request.user.is_staff or request.user.is_admin):
    return redirect('home')
```

---

## 5. Fluxo do Sistema — Regras de Negócio

### 5.1 Submissão de CV (Candidato)

1. Candidato faz upload do PDF em `/upload/`
2. Sistema guarda o ficheiro em `media/resumes/` (BD de documentos)
3. Sistema extrai o texto: primeiro tenta `pdfplumber`; se texto < 50 chars, usa OCR com `pytesseract`
4. Texto limpo é guardado em `resume.parsed_text`
5. Django envia `{resume_id, cv_text, callback_url}` ao webhook do n8n via HTTP POST
6. n8n passa o texto ao Ollama (llama3.2) com o prompt de análise
7. Ollama devolve JSON com `{score, skills, summary, experience, education, languages, feedback}`
8. n8n faz POST ao endpoint `/api/resume/<id>/ai-result/` do Django
9. Django actualiza o Resume com os dados da IA e define `ai_processed=True`
10. Candidato vê o feedback geral do seu CV (não o score de correspondência com vagas)

### 5.2 Candidatura a uma Vaga (Candidato)

1. Candidato deve ter CV submetido (verificar `hasattr(user, 'resume')`)
2. Clicar "Candidatar-me" na listagem de vagas
3. Sistema cria objecto `Application(candidate, job, status='pending')`
4. Sistema envia para n8n: `{application_id, candidate_skills, candidate_summary, candidate_experience, job_requirements, job_title, callback_url}`
5. n8n+Ollama calcula score de similaridade candidato x vaga
6. n8n POST ao endpoint `/api/application/<id>/score-result/`
7. Django actualiza `application.similarity_score` e `application.match_feedback`

### 5.3 Visão do Recrutador

- **Quem vê o score de correspondência:** apenas o recrutador (similarity_score da Application)
- **Quem vê o feedback geral do CV:** o candidato e o recrutador (resume.feedback)
- **Dashboard filtrado por:** vaga, score mínimo, skills, status da candidatura
- **Acções do recrutador:** pré-seleccionar, rejeitar candidatos

---

## 6. Endpoints da API REST

### Existentes
```
GET/POST  /api/resumes/              # Lista/cria resumes (DRF ViewSet)
GET       /api/profile/              # Perfil do utilizador actual
```

### A Criar
```
POST  /api/resume/<id>/ai-result/         # Callback do n8n após análise do CV
POST  /api/application/<id>/score-result/ # Callback do n8n após score de candidatura
POST  /api/application/<id>/update-status/ # Recrutador pré-selecciona ou rejeita
```

### Autenticação dos Callbacks n8n
Os endpoints de callback devem verificar o header `X-Kubuka-Secret` contra `settings.N8N_CALLBACK_SECRET`. Permissão `AllowAny` (o n8n não tem sessão Django).

---

## 7. Integração n8n + Ollama

### Variáveis de ambiente necessárias
```env
N8N_WEBHOOK_CV_URL=http://localhost:5678/webhook/cv-analysis
N8N_WEBHOOK_SCORE_URL=http://localhost:5678/webhook/job-scoring
N8N_CALLBACK_SECRET=kubuka-secret-token-2025
DJANGO_BASE_URL=http://localhost:8000
```

### Prompt para análise de CV (n8n → Ollama)
```
Analisa o seguinte currículo e devolve APENAS um JSON válido, sem texto adicional,
com esta estrutura exacta:
{
  "score": <número inteiro 0-100, qualidade geral do CV>,
  "skills": ["competência1", "competência2", ...],
  "summary": "<resumo profissional extraído ou gerado>",
  "experience": "<experiência profissional estruturada>",
  "education": "<formação académica>",
  "languages": "<idiomas encontrados>",
  "feedback": "<análise com pontos fortes e sugestões de melhoria>"
}

Currículo:
{{cv_text}}
```

### Prompt para score de candidatura (n8n → Ollama)
```
Compara o perfil do candidato com os requisitos da vaga e devolve APENAS um JSON válido:
{
  "similarity_score": <número inteiro 0-100>,
  "match_feedback": "<explicação da correspondência, pontos fortes e lacunas>"
}

Perfil do candidato:
Skills: {{candidate_skills}}
Resumo: {{candidate_summary}}
Experiência: {{candidate_experience}}

Vaga: {{job_title}}
Requisitos: {{job_requirements}}
```

---

## 8. Padrões de Código a Seguir

### Views
- Views HTML: usar `render()`, `redirect()`, `get_object_or_404()`
- Protecção de views: `@login_required` para funções, `LoginRequiredMixin` para classes
- Verificação de role no início da view, antes de qualquer lógica
- Mensagens de feedback: sempre usar `django.contrib.messages`

### Templates
- Sempre extender `recruitment/base.html`
- Usar classes Tailwind CSS e componentes Flowbite
- Mensagens de erro: `bg-red-100 text-red-700`
- Mensagens de sucesso: `bg-green-100 text-green-700`
- Mensagens de info: `bg-blue-100 text-blue-700`

### API Views
- Usar `APIView` para endpoints simples (callbacks)
- Usar `ModelViewSet` para CRUD completo
- Sempre devolver `Response({'success': True})` ou `Response({'error': '...'}, status=400)`

### Migrations
- Sempre correr `python manage.py makemigrations` após alterar models.py
- Nunca editar migrations manualmente salvo necessidade explícita
- Testar com `python manage.py migrate` após criar

### Tratamento de Erros
- Toda a comunicação com n8n/Ollama em blocos `try/except`
- Se n8n estiver indisponível, o sistema continua a funcionar (degraded mode)
- Registar erros com `import logging; logger = logging.getLogger(__name__)`

---

## 9. Estado Actual — O Que Está Feito e o Que Falta

### ✅ Já implementado
- Autenticação (login, logout, signup de candidato)
- Modelo User com `is_candidate` e `is_admin`
- Upload de CV e armazenamento em `media/resumes/`
- Extracção básica de texto com PyPDF2 (a substituir)
- `cv_processor.py` com pdfplumber + OCR (existe mas não está integrado)
- Resume com campos estruturados (summary, skills, experience, education, languages)
- Dashboard do recrutador com lista de candidatos ordenada por score
- Detalhe do currículo / ficha do candidato
- Edição manual dos campos do CV pelo candidato
- Listagem de vagas e candidatura simples (ManyToMany)
- API REST base (resumes, profile)

### ❌ Por implementar (por ordem de prioridade)

**Prioridade 1 — Modelos**
- [ ] Adicionar `is_recruiter` ao User
- [ ] Criar modelo `Application` com `similarity_score` e `status`
- [ ] Adicionar `is_active` e `created_by` ao Job
- [ ] Adicionar `ai_processed` ao Resume
- [ ] Criar e aplicar migration

**Prioridade 2 — Extracção de CV**
- [ ] Corrigir bug em `cv_processor.py` (`tesseract_path` não definido, `POPPLER_INSTRUCTIONS` em falta)
- [ ] Integrar `cv_processor.py` na view `upload_resume` (substituir PyPDF2)
- [ ] Actualizar `requirements.txt` (adicionar pdfplumber, pytesseract, pdf2image, requests)

**Prioridade 3 — Integração n8n**
- [ ] Criar `recruitment/ai_service.py` com `send_cv_to_n8n()` e `send_application_for_scoring()`
- [ ] Criar endpoint `POST /api/resume/<id>/ai-result/` (callback do n8n)
- [ ] Criar endpoint `POST /api/application/<id>/score-result/` (callback do n8n)
- [ ] Adicionar variáveis n8n ao `.env.example` e `settings.py`

**Prioridade 4 — Candidatura com Score**
- [ ] Refactorizar `apply_job` para criar `Application` em vez de usar `job.applicants`
- [ ] Chamar `send_application_for_scoring()` ao criar candidatura
- [ ] Actualizar `job_list.html` para verificar `Application` em vez de `job.applicants`

**Prioridade 5 — Interface do Recrutador**
- [ ] Views para criar/editar/listar vagas (`JobCreateView`, `JobUpdateView`, `JobRecruiterListView`)
- [ ] Templates `job_form.html` e `job_manage.html`
- [ ] Filtros no dashboard (por vaga, score mínimo, skills)
- [ ] Botões de pré-selecção e rejeição no dashboard
- [ ] Endpoint `POST /api/application/<id>/update-status/`

---

## 10. Comandos Úteis

```bash
# Ambiente virtual
python -m venv venv
source venv/bin/activate          # Linux/Mac
venv\Scripts\activate             # Windows

# Dependências
pip install -r requirements.txt

# Base de dados
python manage.py makemigrations   # Após alterar models.py
python manage.py migrate          # Aplicar migrations
python manage.py createsuperuser  # Criar admin

# Servidor de desenvolvimento
python manage.py runserver        # http://localhost:8000

# Testes
python manage.py test             # Correr todos os testes
python manage.py test recruitment # Apenas app recruitment

# Shell Django (para debug)
python manage.py shell

# n8n (em terminal separado)
n8n start                         # http://localhost:5678

# Ollama (em terminal separado)
ollama pull llama3.2              # Download do modelo (1ª vez)
ollama serve                      # Iniciar API em http://localhost:11434
```

---

## 11. Variáveis de Ambiente (.env)

```env
SECRET_KEY=gera-uma-chave-secreta-longa-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# n8n e IA
N8N_WEBHOOK_CV_URL=http://localhost:5678/webhook/cv-analysis
N8N_WEBHOOK_SCORE_URL=http://localhost:5678/webhook/job-scoring
N8N_CALLBACK_SECRET=kubuka-secret-token-2025
DJANGO_BASE_URL=http://localhost:8000
```

---

## 12. Convenções de Nomes

| Elemento | Convenção | Exemplo |
|---|---|---|
| Models | PascalCase | `Application`, `JobPosting` |
| Views (função) | snake_case | `upload_resume`, `apply_job` |
| Views (classe) | PascalCase + sufixo | `ResumeDetailView`, `JobCreateView` |
| URLs (name) | snake_case | `upload_resume`, `job_list` |
| Templates | snake_case.html | `job_form.html`, `dashboard.html` |
| Variáveis de ambiente | UPPER_SNAKE | `N8N_WEBHOOK_CV_URL` |
| Campos do modelo | snake_case | `similarity_score`, `is_recruiter` |

---

*KUBUKA — Sistema de Pré-Selecção Inteligente de Candidatos*  
*Licenciatura em Informática — TFC 2025/2026*
