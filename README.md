# KUBUKA — Pré-Selecção Inteligente de Candidatos

Projecto desenvolvido como Trabalho de Fim de Curso da Licenciatura em Informática (2025/2026). O sistema ajuda empresas angolanas a triarem candidatos de forma mais rápida, usando IA local para analisar CVs e calcular a compatibilidade com as vagas publicadas.

A ideia surgiu da observação de que muitos processos de recrutamento em Angola ainda são feitos manualmente — a empresa recebe dezenas de CVs por email e alguém tem de os ler um a um. O KUBUKA tenta automatizar essa primeira fase.

---

## O que o sistema faz

Há três tipos de utilizadores: **candidatos**, **recrutadores** e **administradores**.

O candidato cria conta, carrega o CV em PDF e candidata-se às vagas que quiser. O sistema extrai automaticamente o texto do CV (com pdfplumber ou OCR se for um PDF digitalizado) e envia para análise por IA — o modelo llama3.2 a correr localmente via Ollama. A IA devolve um score do CV, extrai as competências, experiência, formação, etc.

Quando o candidato se candidata a uma vaga, o sistema calcula também um score de correspondência entre o seu perfil e os requisitos da vaga. Esse score é visível apenas pelo recrutador — o candidato só vê o feedback geral do seu CV.

O recrutador publica vagas, vê os candidatos ordenados por score no dashboard, pode filtrar, pré-seleccionar, agendar entrevistas ou rejeitar. O candidato recebe notificação in-app e por email quando o estado muda.

---

## Stack

- **Backend:** Django 5 + Django REST Framework
- **Frontend:** Django Templates + Tailwind CSS (CDN) + Flowbite
- **Extracção de texto:** pdfplumber + pytesseract (OCR para PDFs digitalizados)
- **IA:** n8n (self-hosted, porta 5678) + Ollama llama3.2 (porta 11434)
- **Base de dados:** SQLite
- **Segurança:** django-axes (bloqueio por força bruta), rate limiting, CSRF, auditoria de acções

---

## Instalar e correr (primeira vez)

### 1. Dependências do sistema

**Python 3.10+** — https://www.python.org/downloads/ (marcar "Add Python to PATH")

**Node.js 18+** — https://nodejs.org (versão LTS)

**n8n:**
```bash
npm install -g n8n
```

**Ollama** — https://ollama.com — depois de instalar, descarregar o modelo (2 GB, só uma vez):
```bash
ollama pull llama3.2
```

**OCR (opcional, para PDFs digitalizados):**
```bash
# Windows
choco install tesseract poppler

# Linux
sudo apt install tesseract-ocr poppler-utils
```

---

### 2. Clonar e configurar

```bash
git clone https://github.com/Manuzau/kubuka.git
cd kubuka

python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

pip install -r requirements.txt
```

Copiar o ficheiro de configuração:
```bash
copy .env.example .env    # Windows
# cp .env.example .env    # Linux
```

Editar o `.env` — o essencial para começar:
```env
SECRET_KEY=cola-aqui-uma-chave-longa
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

N8N_WEBHOOK_CV_URL=http://localhost:5678/webhook/cv-analysis
N8N_WEBHOOK_SCORE_URL=http://localhost:5678/webhook/job-scoring
N8N_CALLBACK_SECRET=kubuka-secret-token-2025
DJANGO_BASE_URL=http://127.0.0.1:8000

EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

Para gerar a SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

---

### 3. Base de dados e primeiro utilizador

```bash
python manage.py migrate
python manage.py createsuperuser
```

O superutilizador tem acesso total, incluindo o Django Admin em `/admin/`.

---

### 4. Configurar o n8n

Iniciar o n8n (`n8n start`), abrir `http://localhost:5678` e criar conta.

Depois importar os dois workflows incluídos no repositório em **Workflows → Import from File**:

| Ficheiro | O que faz |
|---|---|
| `n8n_import_cv.json` | Recebe o CV, chama o Ollama, devolve a análise ao Django |
| `n8n_import_scoring.json` | Compara o perfil do candidato com os requisitos da vaga |

Activar ambos com o botão **Active** no canto superior direito.

No n8n, ir a **Settings → Environment Variables** e adicionar:
```
N8N_CALLBACK_SECRET = kubuka-secret-token-2025
```
(tem de ser igual ao valor no `.env` do Django)

---

### 5. Iniciar o sistema

```bash
# Script automático (recomendado no Windows)
.\start.ps1

# Ou manualmente em três terminais
ollama serve
n8n start
python manage.py runserver
```

Aceder em **http://localhost:8000**

---

## Uso diário (sistema já configurado)

Basta correr `.\start.ps1` — o script verifica automaticamente se o Ollama e o n8n estão a correr, inicia-os se não estiverem, e arranca o Django.

---

## Criar contas de teste

| URL | O que faz |
|---|---|
| `/signup/` | Registo de candidato |
| `/signup/recruiter/` | Registo de recrutador (fica pendente de aprovação) |
| `/admin/` | Django Admin (só superutilizador) |

Para aprovar um recrutador: Django Admin → Users → seleccionar o utilizador → activar `is_recruiter` e `recruiter_approved`. Sem `recruiter_approved`, o recrutador não consegue aceder a nada.

---

## Testes automatizados

```bash
python manage.py test recruitment
```

44 testes cobrindo: controlo de acesso por perfil, upload de CV, candidaturas, callbacks da IA, triagem automática, notificações e email.

---

## Nota sobre django-axes

O sistema bloqueia automaticamente após 5 tentativas de login falhadas (durante 1 hora). Para desbloquear durante o desenvolvimento:

```bash
python manage.py axes_reset
```

---

## Módulo de IA — detalhes e limitações

O Django funciona sem o n8n/Ollama — o upload de CVs e as candidaturas funcionam na mesma, apenas sem a análise automática (os scores ficam a 0).

### Desempenho esperado

| Hardware | Tempo por CV |
|---|---|
| GPU NVIDIA ≥ 4 GB VRAM | 5 – 15 segundos |
| CPU moderna + 16 GB RAM | 45 – 90 segundos |
| CPU + 8 GB RAM | 2 – 5 minutos |
| Menos de 8 GB RAM | Pode dar timeout |

Em máquinas com pouca RAM, o modelo tem de usar swap e fica muito lento. Nesse caso há duas alternativas:

**Usar o modelo mais leve:**
```bash
ollama pull llama3.2:1b
```
Depois alterar `"model": "llama3.2"` para `"model": "llama3.2:1b"` nos dois workflows n8n.

**Simular o callback manualmente (útil para demos):**
```bash
curl -X POST http://127.0.0.1:8000/api/resume/<ID>/ai-result/ \
  -H "Content-Type: application/json" \
  -H "X-Kubuka-Secret: kubuka-secret-token-2025" \
  -d "{\"score\": 78, \"skills\": \"Python, Django\", \"summary\": \"Resumo.\", \"experience\": \"Experiência.\", \"education\": \"Formação.\", \"languages\": \"Português\", \"feedback\": \"Bom CV.\"}"
```

### Nota para Windows

O n8n usa `localhost` mas resolve como IPv6 (`::1`). O Ollama e o Django ouvem em IPv4 (`127.0.0.1`). Por isso no `.env` usar sempre `DJANGO_BASE_URL=http://127.0.0.1:8000` e nos workflows n8n usar `http://127.0.0.1:11434/api/generate` (não `localhost`).
