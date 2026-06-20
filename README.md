# KUBUKA — Sistema de Pré-Selecção Inteligente de Candidatos

O KUBUKA é um sistema web que automatiza a triagem de candidatos em empresas angolanas. A ideia surgiu da necessidade de reduzir o tempo que os recrutadores passam a analisar currículos manualmente — o sistema usa IA (Ollama) para ler cada CV, atribuir uma pontuação e comparar o perfil do candidato com os requisitos da vaga.

> Trabalho de Fim de Curso — Licenciatura em Informática, 2025/2026

---

## O que o sistema faz

### Para candidatos
- Registo de conta e edição de perfil
- Upload do CV em PDF — o sistema extrai o texto automaticamente e, se o PDF for digitalizado, usa OCR
- A IA analisa o CV e devolve: pontuação geral, competências, resumo profissional, experiência, formação, idiomas e feedback
- Possibilidade de se candidatar a vagas e acompanhar o estado das candidaturas

### Para recrutadores
- Criação e gestão de vagas (título, empresa, localização, salário, prazo, requisitos)
- Definição de uma pontuação mínima por vaga — candidaturas abaixo desse valor são rejeitadas automaticamente pelo sistema
- Dashboard com todos os candidatos das suas vagas, ordenados por score de compatibilidade
- Vista em tabela e em Kanban com drag-and-drop para mover candidatos entre estados
- Filtros por vaga, pontuação, estado e competências
- Acções de pré-selecção, agendamento de entrevista e rejeição (com notificação automática ao candidato)
- Painel de análise com gráficos (distribuição de estados, histograma de scores, candidaturas por semana)

### Outras funcionalidades
- Notificações dentro da aplicação quando o estado de uma candidatura muda
- Envio de email automático (configurável via SMTP ou consola em desenvolvimento)
- Protecção contra força bruta: bloqueio automático após 5 tentativas de login falhadas
- 44 testes automatizados

---

## Tecnologias usadas

| Camada | O que usei |
|---|---|
| Backend | Django 5.x + Django REST Framework |
| Frontend | Django Templates + Tailwind CSS (via CDN) + Flowbite |
| Extracção de CV | pdfplumber + pytesseract (OCR) + pdf2image |
| IA e automação | Ollama (llama3.2) + n8n |
| Base de dados | PostgreSQL |
| Configuração | django-environ (.env) |
| Segurança | django-axes |

---

## Arranque rápido

Se já tens tudo instalado e configurado (ver secção seguinte), para arrancar o sistema basta:

**Windows — duplo clique em:**
```
run_project.bat
```

**Ou no PowerShell:**
```powershell
.\start.ps1
```

O script trata de tudo automaticamente:
1. Verifica se o PostgreSQL está a correr na porta 5432
2. Inicia o Ollama se não estiver a correr e verifica se o modelo `llama3.2` está disponível
3. Abre o n8n numa nova janela se não estiver a correr
4. Aplica migrações Django pendentes
5. Arranca o Django em `http://localhost:8000`

---

## Instalação de raiz (novo computador)

### 1. Instalar as ferramentas necessárias

**Python 3.10 ou superior**
Descarrega em https://www.python.org/downloads/ — durante a instalação marca a opção "Add Python to PATH".

**PostgreSQL 14 ou superior**
Descarrega em https://www.postgresql.org/download/ e guarda a palavra-passe do utilizador `postgres` — vais precisar dela a seguir.

**Node.js 18+** (necessário para o n8n)
Descarrega a versão LTS em https://nodejs.org/

**n8n**
```bash
npm install -g n8n
```

**Ollama**
Descarrega e instala em https://ollama.com. Depois de instalado, descarrega o modelo de IA (só é preciso fazer isto uma vez, ocupa cerca de 2 GB):
```bash
ollama pull llama3.2
```

**Tesseract e Poppler** *(opcional — só necessário para PDFs digitalizados)*
```bash
# Windows, com Chocolatey
choco install tesseract poppler
```

---

### 2. Clonar o repositório

```bash
git clone https://github.com/Manuzau/kubuka.git
cd kubuka
```

---

### 3. Criar o ambiente virtual Python

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

---

### 4. Instalar as dependências Python

```bash
pip install -r requirements.txt
```

---

### 5. Configurar o PostgreSQL

#### 5a. Criar a base de dados e o utilizador

Abre o **SQL Shell (psql)** que vem com o PostgreSQL (ou usa o pgAdmin) e executa:

```sql
CREATE DATABASE kubuka_db;
CREATE USER kubuka_user WITH PASSWORD 'kubuka_pass';
GRANT ALL PRIVILEGES ON DATABASE kubuka_db TO kubuka_user;
ALTER USER kubuka_user CREATEDB;
```

> O `CREATEDB` é necessário para o Django poder criar a base de dados temporária quando correres os testes (`python manage.py test`).

Se preferires via linha de comandos (com o `postgres` no PATH):
```bash
createdb kubuka_db
createuser kubuka_user
psql -U postgres -c "ALTER USER kubuka_user WITH PASSWORD 'kubuka_pass';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE kubuka_db TO kubuka_user;"
psql -U postgres -c "ALTER USER kubuka_user CREATEDB;"
```

#### 5b. Configurar o PostgreSQL para arrancar automaticamente com o Windows

Por omissão, o PostgreSQL fica como arranque manual após a instalação. Para que arranque sozinho sempre que ligares o computador (e o `start.ps1` o encontre sem erros):

**Opção A — via linha de comandos (recomendado, requer PowerShell como Administrador):**
```powershell
Set-Service -Name "postgresql-x64-18" -StartupType Automatic
Start-Service -Name "postgresql-x64-18"
```

> Se a tua versão do PostgreSQL for diferente, ajusta o número. Para ver o nome exacto do serviço: `Get-Service | Where-Object { $_.DisplayName -like "*postgresql*" }`

**Opção B — via interface gráfica:**
1. Abre o **Gestor de Serviços do Windows**: prime `Win + R` → escreve `services.msc` → Enter
2. Procura o serviço `postgresql-x64-18` (ou similar)
3. Clica com o botão direito → **Propriedades**
4. Em **Tipo de arranque**, selecciona **Automático**
5. Clica em **Iniciar** se o serviço não estiver já a correr
6. Clica em **OK**

Após esta configuração, o PostgreSQL arranca antes do `start.ps1` e nunca precisas de o iniciar manualmente.

---

### 6. Ficheiro de configuração .env

```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

Abre o ficheiro `.env` e preenche:

```env
SECRET_KEY=cola-aqui-uma-chave-longa-e-aleatoria
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=kubuka_db
DB_USER=kubuka_user
DB_PASSWORD=kubuka_pass
DB_HOST=localhost
DB_PORT=5432

N8N_WEBHOOK_CV_URL=http://localhost:5678/webhook/cv-analysis
N8N_WEBHOOK_SCORE_URL=http://localhost:5678/webhook/job-scoring
N8N_CALLBACK_SECRET=kubuka-secret-token-2025
DJANGO_BASE_URL=http://127.0.0.1:8000

EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

Para gerar a `SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

> **Nota para Windows:** usa sempre `127.0.0.1` em vez de `localhost` no `DJANGO_BASE_URL`. O Node.js resolve `localhost` como IPv6 (`::1`) mas o Django ouve em IPv4 — se ficares com `localhost` o n8n não consegue chamar o Django.

---

### 7. Aplicar as migrações e criar o administrador

```bash
python manage.py migrate
python manage.py createsuperuser
```

---

### 8. Importar os workflows do n8n

Inicia o n8n (`n8n start`) e acede a `http://localhost:5678`. Cria uma conta na primeira execução.

Depois vai a **Workflows → Import from File** e importa os dois ficheiros que estão na raiz do projecto:

| Ficheiro | O que faz |
|---|---|
| `n8n_workflow_kubuka.json` | Recebe o texto do CV, envia ao Ollama e devolve a análise ao Django |
| `n8n_workflow_job_scoring.json` | Compara o perfil do candidato com os requisitos da vaga e calcula o score |

Activa cada workflow com o botão **Active** (canto superior direito de cada workflow).

---

### 9. Arrancar o sistema

```bash
# Recomendado — script automático (trata de tudo)
.\start.ps1

# Ou manualmente, em três terminais separados
ollama serve                   # terminal 1
n8n start                      # terminal 2
python manage.py runserver     # terminal 3
```

A aplicação fica disponível em **http://localhost:8000**.

---

### 10. Correr os testes

```bash
python manage.py test recruitment
```

---

## Modelo Ollama — recomendação do tutor

Por defeito o sistema usa o `llama3.2` (modelo local, cerca de 2 GB de RAM). O tutor recomendou também suporte a modelos cloud para quando o hardware disponível for limitado.

Para usar o `nemotron-3-nano:30b-cloud` (modelo cloud, sem necessidade de GPU):

1. Cria conta em https://ollama.com/settings e activa os créditos cloud
2. No `.env` do projecto, define:
```env
OLLAMA_MODEL=nemotron-3-nano:30b-cloud
```
3. Os workflows n8n lêem esta variável automaticamente — não é preciso mais nada

Para voltar ao modelo local: `OLLAMA_MODEL=llama3.2`.

---

## Problemas frequentes

### PostgreSQL não está a correr quando abro o start.ps1

O `start.ps1` verifica o PostgreSQL na porta 5432 e avisa se não estiver disponível. Para resolver de uma vez por todas, configura o serviço para arrancar automaticamente com o Windows (ver **secção 5b** acima).

Para verificar o estado do serviço:
```powershell
Get-Service | Where-Object { $_.DisplayName -like "*postgresql*" }
```

Para iniciar manualmente quando necessário:
```powershell
# PowerShell como Administrador
Start-Service -Name "postgresql-x64-18"
```

---

### Ollama muito lento

O `llama3.2` precisa de cerca de 2 GB de RAM livre. Em máquinas com menos de 8 GB disponíveis, a análise pode demorar vários minutos e o n8n pode dar timeout.

**Opções:**

Usar o modelo mais pequeno (1B parâmetros, mais rápido):
```bash
ollama pull llama3.2:1b
```
Depois, nos workflows n8n, alterar o campo do modelo para `llama3.2:1b`.

Aumentar o timeout no workflow n8n (`n8n_workflow_kubuka.json`, nó Ollama):
```json
"options": { "timeout": 600000 }
```

Simular a resposta da IA directamente via API (útil para testes e demonstrações sem precisar do Ollama):
```bash
curl -X POST http://127.0.0.1:8000/api/resume/1/ai-result/ \
  -H "Content-Type: application/json" \
  -H "X-Kubuka-Secret: kubuka-secret-token-2025" \
  -d "{\"score\": 78, \"skills\": \"Python, Django\", \"summary\": \"Candidato com experiência em backend.\", \"experience\": \"2 anos de desenvolvimento web.\", \"education\": \"Licenciatura em Informática.\", \"languages\": \"Português, Inglês\", \"feedback\": \"Bom perfil técnico.\"}"
```

---

### Conta bloqueada após tentativas de login falhadas

```bash
python manage.py axes_reset

# ou para um utilizador específico:
python manage.py axes_reset_user <username>
```

---

### `localhost` vs `127.0.0.1` no Windows

O n8n (Node.js) resolve `localhost` como `::1` (IPv6) no Windows, mas o Django e o Ollama ouvem em `127.0.0.1` (IPv4). Por isso:
- No `.env` usa `DJANGO_BASE_URL=http://127.0.0.1:8000`
- Nos workflows n8n usa `http://127.0.0.1:11434/api/generate` para o Ollama
- Nos workflows n8n usa `http://127.0.0.1:8000` para os callbacks do Django

---

## Contas de teste

Depois de criar o superutilizador, podes criar contas directamente na aplicação:

| URL | O que faz |
|---|---|
| `/signup/` | Criar conta de candidato |
| `/signup/recruiter/` | Registar conta de recrutador (fica pendente de aprovação) |
| `/admin/` | Django Admin — gestão completa do sistema |

Para aprovar um recrutador: **Django Admin → Users → seleccionar o utilizador → activar `is_recruiter` e `recruiter_approved`**.

---

## Como o sistema funciona (resumo)

```
Candidato faz upload do CV
    |
    v
Django extrai o texto (pdfplumber / OCR se necessário)
    |
    v
Django envia para o n8n via webhook
    |
    v
n8n passa o texto ao Ollama com o prompt de análise
    |
    v
Ollama devolve JSON: score + competências + resumo + experiência + formação + idiomas + feedback
    |
    v
n8n faz callback para /api/resume/<id>/ai-result/
    |
    v
Django actualiza o perfil do candidato

─────────────────────────────────────────────

Candidato candidata-se a uma vaga
    |
    v
Django cria o registo Application e envia para o n8n
    |
    v
Ollama compara o perfil com os requisitos da vaga
    |
    v
n8n faz callback para /api/application/<id>/score-result/
    |
    v
Django guarda o score de compatibilidade (visível só ao recrutador)
Se score < mínimo definido na vaga → candidatura rejeitada automaticamente
```

---

## Estrutura do projecto

```
kubuka/
├── core/
│   ├── settings.py
│   └── urls.py
├── recruitment/
│   ├── models.py            — User, Resume, Job, Application, Notification, AuditLog
│   ├── views.py             — views HTML
│   ├── callback_views.py    — endpoints de callback do n8n
│   ├── ai_service.py        — envio de pedidos ao n8n
│   ├── cv_processor.py      — extracção de texto do PDF
│   ├── notifications.py     — notificações in-app e email
│   ├── rate_limit.py        — rate limiting
│   ├── tests.py             — 44 testes automatizados
│   └── templates/           — HTML com Tailwind + Flowbite
├── n8n_workflow_kubuka.json       — workflow de análise de CV
├── n8n_workflow_job_scoring.json  — workflow de scoring de candidatura
├── start.ps1                — script de arranque (Windows)
├── run_project.bat          — duplo clique para arrancar
├── .env.example
└── requirements.txt
```
