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
| IA | Ollama (llama3.2:1b) — chamado directamente pelo Django |
| Base de dados | PostgreSQL |
| Configuração | django-environ (.env) |
| Segurança | django-axes |

---

## Como o sistema funciona (resumo)

```
Candidato faz upload do CV
    |
    v
Django extrai o texto (pdfplumber / OCR se necessário)
    |
    v
Django chama o Ollama directamente via HTTP (ai_service.py)
    |
    v
Ollama devolve JSON: score + competências + resumo + experiência + formação + idiomas + feedback
    |
    v
Django actualiza o perfil do candidato na base de dados

─────────────────────────────────────────────

Candidato candidata-se a uma vaga
    |
    v
Django cria o registo Application
    |
    v
Django chama o Ollama directamente para comparar o perfil com os requisitos
    |
    v
Django guarda o score de compatibilidade (visível só ao recrutador)
Se score < mínimo definido na vaga → candidatura rejeitada automaticamente
```

> **Nota de arquitectura:** o Django chama o Ollama directamente (porta 11434) sem intermediário. Os ficheiros `n8n_workflow_*.json` na raiz do projecto são mantidos como referência histórica mas não são necessários para o sistema funcionar.

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
2. Inicia o Ollama se não estiver a correr e verifica se o modelo `llama3.2:1b` está disponível
3. Aplica migrações Django pendentes
4. Arranca o Django em `http://localhost:8000`

---

## Instalação de raiz (novo computador)

### 1. Instalar as ferramentas necessárias

**Python 3.10 ou superior**
Descarrega em https://www.python.org/downloads/ — durante a instalação marca a opção "Add Python to PATH".

**PostgreSQL 14 ou superior**
Descarrega em https://www.postgresql.org/download/ e guarda a palavra-passe do utilizador `postgres` — vais precisar dela a seguir.

**Ollama**
Descarrega e instala em https://ollama.com. Depois de instalado, descarrega o modelo de IA (só é preciso fazer isto uma vez, ocupa cerca de 1.3 GB):
```bash
ollama pull llama3.2:1b
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

Por omissão, o PostgreSQL fica como arranque manual após a instalação. Para que arranque sozinho sempre que ligares o computador:

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

DJANGO_BASE_URL=http://127.0.0.1:8000

EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

Para gerar a `SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

---

### 7. Aplicar as migrações e criar o administrador

```bash
python manage.py migrate
python manage.py createsuperuser
```

---

### 8. Arrancar o sistema

```bash
# Recomendado — script automático (trata de tudo)
.\start.ps1

# Ou manualmente, em dois terminais separados
ollama serve                   # terminal 1
python manage.py runserver     # terminal 2
```

A aplicação fica disponível em **http://localhost:8000**.

---

### 9. Correr os testes

```bash
python manage.py test recruitment
```

---

## Modelo Ollama

O sistema usa o `llama3.2:1b` (1B parâmetros, 1.3 GB, ~15–25 segundos por análise). Este modelo está fixo em `recruitment/ai_service.py` e foi escolhido por funcionar bem em hardware com memória RAM limitada.

O modelo `llama3.2` (3B parâmetros) foi testado mas ultrapassava os 120 segundos por análise na máquina de desenvolvimento — por isso foi descartado.

Para usar um modelo diferente, altera a constante `OLLAMA_MODEL` em `recruitment/ai_service.py`:
```python
OLLAMA_MODEL = 'llama3.2:1b'   # padrão — recomendado
# OLLAMA_MODEL = 'llama3.2'    # se tiveres 8+ GB de RAM livre
```

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

### Ollama muito lento ou a dar timeout

O modelo padrão é o `llama3.2:1b` (~15–25s por análise). Se mesmo assim estiver lento, é sinal de que a RAM disponível é muito pouca.

Verifica a RAM livre:
```powershell
(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB
# resultado em GB — precisa de pelo menos 1.5 GB livres
```

O timeout do Django para chamadas ao Ollama é de 180 segundos (definido em `ai_service.py`). Se precisares de aumentar:
```python
OLLAMA_TIMEOUT = 300  # segundos
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

## Contas de teste

Depois de criar o superutilizador, podes criar contas directamente na aplicação:

| URL | O que faz |
|---|---|
| `/signup/` | Criar conta de candidato |
| `/signup/recruiter/` | Registar conta de recrutador (fica pendente de aprovação) |
| `/admin/` | Django Admin — gestão completa do sistema |

Para aprovar um recrutador: **Django Admin → Users → seleccionar o utilizador → activar `is_recruiter` e `recruiter_approved`**.

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
│   ├── callback_views.py    — endpoints de callback (legado, mantidos para compatibilidade)
│   ├── ai_service.py        — chama o Ollama directamente e actualiza a BD
│   ├── cv_processor.py      — extracção de texto do PDF
│   ├── notifications.py     — notificações in-app e email
│   ├── rate_limit.py        — rate limiting
│   ├── tests.py             — 44 testes automatizados
│   └── templates/           — HTML com Tailwind + Flowbite
├── n8n_workflow_kubuka.json       — referência histórica (não usado pelo sistema)
├── n8n_workflow_job_scoring.json  — referência histórica (não usado pelo sistema)
├── start.ps1                — script de arranque (Windows)
├── run_project.bat          — duplo clique para arrancar
├── .env.example
└── requirements.txt
```
