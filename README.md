# KUBUKA — Sistema de Pré-Selecção Inteligente de Candidatos

Sistema web que automatiza a triagem e pré-selecção de candidatos para empresas angolanas, utilizando Inteligência Artificial local (Ollama) para analisar currículos e calcular scores de compatibilidade com vagas de emprego.

> Trabalho de Fim de Curso (TFC) — Licenciatura em Informática, 2025/2026

---

## O Que Foi Implementado

### Autenticação e Perfis
- Registo, login e logout com três perfis distintos: **Candidato**, **Recrutador** e **Administrador**
- Edição de perfil (nome, email, empresa)
- Recuperação de palavra-passe por email

### Gestão de Currículos (Candidato)
- Upload de CV em PDF com extracção automática de texto (pdfplumber + OCR via pytesseract para PDFs digitalizados)
- Envio do texto para análise por IA (n8n + Ollama llama3.2) que extrai: pontuação geral, competências, resumo, experiência, formação, idiomas e feedback
- Visualização e edição manual da ficha do CV
- Score e feedback do CV visível pelo candidato no perfil

### Gestão de Vagas (Recrutador)
- Criação, edição e publicação de vagas com todos os campos (título, empresa, localização, salário, prazo, requisitos, etc.)
- Definição de **score mínimo** por vaga (triagem automática)

### Candidaturas
- Candidato aplica a vagas — cria um registo `Application`
- n8n + Ollama calcula o **score de correspondência** entre o perfil do candidato e os requisitos da vaga
- **Triagem automática**: candidaturas abaixo do score mínimo são rejeitadas automaticamente

### Dashboard do Recrutador
- Vista em **tabela** (paginada) e **Kanban** com drag-and-drop entre colunas de estado
- Filtros por vaga, score mínimo, status da candidatura e pesquisa por skills
- Acções de pré-selecção, agendamento de entrevista e rejeição com notificação automática ao candidato
- Painel de **análise com gráficos** (Chart.js): distribuição de estados, top vagas, histograma de scores, candidaturas por semana

### Notificações
- Notificações in-app para o candidato quando o estado da candidatura muda
- Envio de email automático (configurável via SMTP ou consola em desenvolvimento)

### API REST
- Endpoints de callback para o n8n actualizar resultados da IA no Django
- Endpoint para o recrutador alterar o estado de candidaturas via API

### Testes Automatizados
- 43 testes cobrindo: autenticação, upload de CV, candidaturas, callbacks da IA, triagem automática, notificações e email

---

## Stack Tecnológico

| Camada | Tecnologia |
|---|---|
| Backend | Django 5.x + Django REST Framework |
| Frontend | Django Templates + Tailwind CSS (CDN) + Flowbite |
| Extracção de CV | pdfplumber + pytesseract (OCR) + pdf2image |
| Automação / IA | n8n (self-hosted) + Ollama llama3.2 (local) |
| Base de dados | SQLite |
| Configuração | django-environ (.env) |

---

## Pré-requisitos

- Python 3.10 ou superior
- [Ollama](https://ollama.com) instalado e a correr localmente
- [n8n](https://n8n.io) instalado (via npm ou npx)
- *(Opcional, para OCR)* Tesseract e Poppler instalados no sistema

---

## Como Executar o Projecto

### 1. Clonar o repositório

```bash
git clone https://github.com/Manuzau/kubuka.git
cd kubuka
```

### 2. Criar e activar o ambiente virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

### 3. Instalar dependências Python

```bash
pip install -r requirements.txt
```

> **Nota OCR (opcional):** Para extrair texto de PDFs digitalizados é necessário instalar:
> - **Windows:** `choco install tesseract poppler`
> - **Linux:** `sudo apt install tesseract-ocr poppler-utils`
> 
> Sem estas ferramentas o sistema continua a funcionar para PDFs com texto embebido.

### 4. Configurar variáveis de ambiente

```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

Edita o ficheiro `.env` e define pelo menos a `SECRET_KEY`:

```env
SECRET_KEY=coloca-aqui-uma-chave-longa-e-aleatória
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

N8N_WEBHOOK_CV_URL=http://localhost:5678/webhook/cv-analysis
N8N_WEBHOOK_SCORE_URL=http://localhost:5678/webhook/job-scoring
N8N_CALLBACK_SECRET=kubuka-secret-token-2025
# Usar 127.0.0.1 em vez de localhost (importante no Windows — ver secção de requisitos de hardware)
DJANGO_BASE_URL=http://127.0.0.1:8000

EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

### 5. Aplicar migrações e criar administrador

```bash
python manage.py migrate
python manage.py createsuperuser
```

O superutilizador criado terá acesso total ao sistema, incluindo o Django Admin em `/admin/`.

### 6. Iniciar o servidor

```bash
python manage.py runserver
```

Acede em: **http://localhost:8000**

### 7. Correr os testes automatizados

```bash
python manage.py test recruitment
```

---

## Configurar o n8n e Ollama (Módulo de IA)

O módulo de IA é **opcional para testar o sistema base** — o Django funciona sem ele (modo degradado). Para activar a análise automática de CVs e o scoring de candidaturas, seguir os passos abaixo.

### Passo 1 — Instalar e iniciar o Ollama

1. Descarregar e instalar o Ollama em [https://ollama.com](https://ollama.com)
2. Descarregar o modelo llama3.2 (primeira execução — cerca de 2 GB):

```bash
ollama pull llama3.2
```

3. O Ollama inicia automaticamente em segundo plano. Para verificar:

```bash
ollama list
```

O serviço fica disponível em `http://localhost:11434`.

---

### Passo 2 — Instalar e iniciar o n8n

```bash
# Com npm (recomendado)
npm install -g n8n
n8n start

# Ou com npx (sem instalação permanente)
npx n8n start
```

O n8n abre em **http://localhost:5678**. Cria uma conta na primeira execução.

---

### Passo 3 — Configurar a variável de ambiente no n8n

No painel do n8n, vai a **Settings → Environment Variables** e adiciona:

| Nome | Valor |
|---|---|
| `N8N_CALLBACK_SECRET` | `kubuka-secret-token-2025` |

> Este valor deve ser igual ao definido no `.env` do Django.

---

### Passo 4 — Importar os workflows

No n8n, vai a **Workflows → Import from File** (ou Import from JSON) e importa os dois ficheiros:

| Ficheiro | Função |
|---|---|
| `n8n_workflow_kubuka.json` | Análise de CV — extrai score, competências, resumo, experiência, formação, idiomas e feedback |
| `n8n_workflow_job_scoring.json` | Scoring de candidatura — calcula a correspondência entre o perfil do candidato e os requisitos da vaga |

---

### Passo 5 — Activar os workflows

Após importar cada workflow, clica no botão **Active** (canto superior direito) para os activar.

Os webhooks ficam disponíveis em:
- `http://localhost:5678/webhook/cv-analysis`
- `http://localhost:5678/webhook/job-scoring`

---

### Passo 6 — Verificar a ligação

Para confirmar que tudo está ligado, faz o upload de um CV na aplicação como candidato. Após o upload, o sistema deve:
1. Guardar o CV e extrair o texto
2. Enviar para o n8n (verificar em Executions no painel n8n)
3. O n8n chama o Ollama e recebe a análise
4. O Django é notificado e actualiza o perfil do candidato com o score e feedback

> Se o n8n não estiver a correr, o upload funciona na mesma — apenas sem a análise automática de IA.

---

## Requisitos de Hardware para o Módulo de IA

O desempenho do módulo de IA (Ollama + llama3.2) depende directamente do hardware disponível.

### Configurações testadas

| Hardware | Tempo de análise de CV | Viável? |
|---|---|---|
| GPU dedicada (NVIDIA ≥ 4 GB VRAM) | 5 – 15 segundos | ✅ Recomendado |
| CPU moderna + 16 GB RAM | 45 – 90 segundos | ✅ Aceitável |
| CPU + 8 GB RAM | 2 – 5 minutos | ⚠️ Lento mas funcional |
| CPU + menos de 8 GB RAM | > 5 minutos ou timeout | ❌ Não recomendado |

### Limitação conhecida — CPU com pouca RAM

O modelo `llama3.2` (3B parâmetros) ocupa aproximadamente **2 GB de RAM** só para os pesos. Em máquinas com menos de 8 GB de RAM disponível, o sistema operativo recorre ao disco (swap/paginação), tornando a inferência extremamente lenta.

**Sintomas:** o n8n regista `500 — timeout` após 2–10 minutos; o campo `ai_processed` do Resume permanece `False`.

### Soluções para ambientes com hardware limitado

**Opção A — Ajustar o timeout do workflow n8n**

No ficheiro `n8n_workflow_kubuka.json`, no nó `Ollama — Analisar CV`, aumentar o campo `timeout` para `600000` (10 minutos):

```json
"options": { "timeout": 600000 }
```

**Opção B — Usar o modelo de 1B parâmetros (mais rápido)**

```bash
ollama pull llama3.2:1b
```

Depois, alterar `"model": "llama3.2"` para `"model": "llama3.2:1b"` nos dois workflows n8n.

**Opção C — Simular o callback manualmente (para testes/demo)**

O Django aceita o resultado da IA directamente via endpoint REST, sem necessitar do n8n+Ollama:

```bash
curl -X POST http://127.0.0.1:8000/api/resume/<ID>/ai-result/ \
  -H "Content-Type: application/json; charset=utf-8" \
  -H "X-Kubuka-Secret: kubuka-secret-token-2025" \
  -d '{
    "score": 75,
    "skills": "Python, Django, SQL",
    "summary": "Resumo do candidato.",
    "experience": "Experiência profissional.",
    "education": "Formação académica.",
    "languages": "Português, Inglês",
    "feedback": "Feedback sobre o CV."
  }'
```

### Nota sobre Windows — usar 127.0.0.1 em vez de localhost

No Windows, o Node.js (n8n) resolve `localhost` como `::1` (IPv6) por omissão, mas o Ollama e o Django ouvem em `127.0.0.1` (IPv4). Usar sempre o IP explícito:

```env
# .env
DJANGO_BASE_URL=http://127.0.0.1:8000
```

E nos workflows n8n, a URL do Ollama deve ser `http://127.0.0.1:11434/api/generate` (não `http://localhost:11434/api/generate`).

---

## Fluxo Resumido do Sistema

```
Candidato faz upload de CV
        │
        ▼
Django extrai texto do PDF (pdfplumber / OCR)
        │
        ▼
Django envia para n8n (webhook cv-analysis)
        │
        ▼
n8n envia o texto ao Ollama llama3.2
        │
        ▼
Ollama devolve JSON com score + 6 campos estruturados
        │
        ▼
n8n faz POST de callback para /api/resume/<id>/ai-result/
        │
        ▼
Django actualiza o CV com os dados da IA
        │
        ▼
Candidato vê score e feedback no perfil

────────────────────────────────────────────

Candidato candidata-se a uma vaga
        │
        ▼
Django cria registo Application + envia para n8n (webhook job-scoring)
        │
        ▼
Ollama compara perfil do candidato com requisitos da vaga
        │
        ▼
n8n faz POST de callback para /api/application/<id>/score-result/
        │
        ▼
Django actualiza similarity_score (visível apenas ao recrutador)
Se score < mínimo definido na vaga → candidatura rejeitada automaticamente
```

---

## Contas de Teste

Após `createsuperuser`, pode criar contas de teste diretamente na aplicação:

| URL | Acção |
|---|---|
| `/signup/` | Criar conta de candidato |
| `/admin/` | Django Admin (superutilizador) — pode promover utilizadores a recrutador |

Para promover um utilizador a **Recrutador**, acede ao Django Admin → Users → selecciona o utilizador → activa o campo `is_recruiter`.

---

## Estrutura do Projecto

```
kubuka/
├── core/                        # Configurações Django
├── recruitment/
│   ├── models.py                # User, Resume, Job, Application, Notification
│   ├── views.py                 # Views HTML
│   ├── api_views.py             # Endpoints REST (callbacks n8n, status)
│   ├── callback_views.py        # Endpoints de callback do n8n
│   ├── ai_service.py            # Envio de pedidos ao n8n
│   ├── notifications.py         # Notificações in-app e email
│   ├── cv_processor.py          # Extracção de texto de PDF
│   ├── tests.py                 # 43 testes automatizados
│   └── templates/               # Templates HTML
├── n8n_workflow_kubuka.json      # Workflow n8n — análise de CV
├── n8n_workflow_job_scoring.json # Workflow n8n — scoring de candidatura
├── .env.example                 # Variáveis de ambiente de exemplo
└── requirements.txt
```
