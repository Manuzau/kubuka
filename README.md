# KUBUKA — Sistema de Pré-Selecção Inteligente de Candidatos

[![CI](https://github.com/Manuzau/kubuka/actions/workflows/ci.yml/badge.svg)](https://github.com/Manuzau/kubuka/actions/workflows/ci.yml)

O KUBUKA é um sistema web que automatiza a triagem de candidatos em empresas angolanas. A ideia surgiu da necessidade de reduzir o tempo que os recrutadores passam a analisar currículos manualmente — o sistema usa IA local (Ollama) para ler cada CV, atribuir uma pontuação e comparar o perfil do candidato com os requisitos da vaga.

> Trabalho de Fim de Curso — Licenciatura em Informática, 2025/2026

---

## Índice

- [O que o sistema faz](#o-que-o-sistema-faz)
- [Tecnologias usadas](#tecnologias-usadas)
- [Como o sistema funciona](#como-o-sistema-funciona)
- [Arranque rápido (dia-a-dia)](#arranque-rápido-dia-a-dia)
- [Instalação de raiz num computador novo](#instalação-de-raiz-num-computador-novo)
- [Testes automatizados](#testes-automatizados)
- [Deploy em produção](#deploy-em-produção)
- [Estrutura do projecto](#estrutura-do-projecto)
- [Problemas frequentes](#problemas-frequentes)

---

## O que o sistema faz

### Para candidatos
- Registo de conta e edição de perfil
- Upload do CV em PDF — o sistema extrai o texto automaticamente e, se for um PDF digitalizado, usa OCR
- A IA analisa o CV e devolve: pontuação geral, competências, resumo profissional, experiência, formação, idiomas e feedback
- Candidatura a vagas e acompanhamento do estado das candidaturas

### Para recrutadores
- Criação e gestão de vagas (título, empresa, localização, salário, prazo, requisitos)
- Definição de uma pontuação mínima por vaga — candidaturas abaixo desse valor são rejeitadas automaticamente
- Dashboard com todos os candidatos das suas vagas, ordenados por score de compatibilidade
- Vista em tabela e em Kanban com drag-and-drop para mover candidatos entre estados
- Filtros por vaga, pontuação, estado e competências
- Acções de pré-selecção, agendamento de entrevista e rejeição (com notificação automática ao candidato)
- Painel de análise com gráficos (distribuição de estados, histograma de scores, candidaturas por semana)

### Outras funcionalidades
- Notificações dentro da aplicação quando o estado de uma candidatura muda
- Envio de email automático (SMTP em produção, consola em desenvolvimento)
- Protecção contra força bruta: bloqueio automático após 5 tentativas de login falhadas
- 44 testes automatizados

---

## Tecnologias usadas

| Camada | O que usei |
|---|---|
| Backend | Django 5.x + Django REST Framework |
| Frontend | Django Templates + Tailwind CSS (via CDN) + Flowbite |
| Extracção de CV | pdfplumber + pytesseract (OCR) + pdf2image |
| IA local | Ollama com dois modelos (llama3.2:1b e qwen2.5:3b) |
| Automação | n8n (workflows self-hosted) |
| Base de dados | PostgreSQL |
| Configuração | django-environ (.env) |
| Segurança | django-axes |
| Produção | gunicorn + WhiteNoise, Docker, CI (GitHub Actions) |

---

## Como o sistema funciona

```
Candidato faz upload do CV
    |
    v
Django extrai o texto (pdfplumber ou OCR)
    |
    v
Django envia para o n8n via webhook
    |
    v
n8n passa o texto ao Ollama (llama3.2:1b)
    |
    v
Ollama devolve JSON com: score, competências, resumo, experiência, formação, idiomas, feedback
    |
    v
n8n faz callback para /api/resume/<id>/ai-result/
    |
    v
Django actualiza o perfil na base de dados

--------------------------------------------------

Candidato candidata-se a uma vaga
    |
    v
Django cria o registo Application e envia para o n8n
    |
    v
n8n + Ollama (qwen2.5:3b) comparam o perfil com os requisitos
    |
    v
n8n faz callback para /api/application/<id>/score-result/
    |
    v
Django guarda o score de compatibilidade (visível só ao recrutador)
Se score < mínimo definido na vaga → candidatura rejeitada automaticamente
```

**Porquê dois modelos?**
- `llama3.2:1b` (1.3 GB, ~70s) é usado para **análise de CV** — rápido e suficiente para extrair texto estruturado.
- `qwen2.5:3b` (1.9 GB, ~2 min) é usado para **scoring de candidaturas** — muito melhor a produzir JSON estruturado e a raciocinar sobre a correspondência entre candidato e vaga.

### IA na cloud (opcional, com fallback automático do Ollama)

Por omissão o KUBUKA usa o Ollama local (razões de privacidade — ver tese). Os workflows do
n8n suportam também a **Groq** (API compatível com OpenAI, gratuita até um limite generoso e
muito rápida) como alternativa, sem qualquer alteração ao código Django, de duas formas:

**Automática (recomendada):** se o Ollama não estiver instalado ou não estiver a correr, o
n8n cai sozinho para a Groq assim que a chamada ao Ollama falhar — não é preciso mudar nada
no `.env`. Só é necessário ter uma `GROQ_API_KEY` configurada:
```env
GROQ_API_KEY=a-tua-chave-aqui
```
Cria a conta/chave em https://console.groq.com/keys.

**Forçada (para demos rápidas):** para ignorar o Ollama por completo e ir sempre directo à
Groq (mais previsível, sem esperar por uma tentativa de ligação ao Ollama primeiro):
```env
AI_PROVIDER=cloud
GROQ_API_KEY=a-tua-chave-aqui
```

Em qualquer dos casos é preciso reiniciar o n8n depois de editar o `.env` (o `start.ps1` faz
isto automaticamente a cada arranque). Para voltar a exigir sempre o Ollama local (sem
fallback), seria necessário remover a ligação de erro no nó "Chamar Ollama" — não recomendado,
pois a rede de segurança automática não tem custo quando o Ollama funciona normalmente.

---

## Arranque rápido (dia-a-dia)

Se já tens tudo instalado (ver secção seguinte), para arrancar:

**Windows — duplo clique em:**
```
run_project.bat
```

**Ou no PowerShell:**
```powershell
.\start.ps1
```

O script trata de tudo automaticamente:

1. Verifica se o **PostgreSQL** está a correr (porta 5432)
2. Inicia o **Ollama** se não estiver a correr e faz download automático dos modelos `llama3.2:1b` e `qwen2.5:3b` se faltarem
3. Abre o **n8n** numa nova janela se não estiver a correr
4. Aplica migrações Django pendentes
5. Arranca o **Django** em `http://localhost:8000`

---

## Instalação de raiz num computador novo

> Assume-se que estás em **Windows 10/11**. Para Linux/macOS, adapta os comandos onde indicado.

### Passo 1 — Instalar ferramentas base

| Ferramenta | Onde | Notas de instalação |
|---|---|---|
| **Python 3.10+** | https://www.python.org/downloads/ | Marca "Add Python to PATH" durante a instalação |
| **Git** | https://git-scm.com/download/win | Aceita as opções padrão |
| **PostgreSQL 14+** | https://www.postgresql.org/download/ | Guarda a palavra-passe do utilizador `postgres` |
| **Node.js LTS** | https://nodejs.org/ | Necessário para o n8n |
| **Ollama** | https://ollama.com | IA local, ocupa ~200 MB antes dos modelos |

**Opcional — apenas se precisares de OCR (PDFs digitalizados):**
```powershell
# Windows com Chocolatey
choco install tesseract poppler
```

### Passo 2 — Configurar o PostgreSQL para arrancar sempre

Por omissão, o serviço fica em arranque manual. Para que arranque sempre que ligares o computador (PowerShell como Administrador):

```powershell
Set-Service -Name "postgresql-x64-18" -StartupType Automatic
Start-Service -Name "postgresql-x64-18"
```

> Se a versão for diferente, ajusta o número. Para descobrir o nome exacto:
> ```powershell
> Get-Service | Where-Object { $_.DisplayName -like "*postgresql*" }
> ```

### Passo 3 — Instalar o n8n globalmente

```bash
npm install -g n8n
```

Verifica com `n8n --version`.

### Passo 4 — Descarregar os modelos Ollama

O `start.ps1` faz isto automaticamente na primeira execução, mas se preferires fazê-lo já (total ~3.2 GB):

```bash
ollama pull llama3.2:1b
ollama pull qwen2.5:3b
```

### Passo 5 — Clonar o repositório

```bash
git clone https://github.com/Manuzau/kubuka.git
cd kubuka
```

### Passo 6 — Criar o ambiente virtual Python

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

Verifica o prompt: deve começar por `(.venv)`.

### Passo 7 — Instalar dependências Python

```bash
pip install -r requirements.txt
```

### Passo 8 — Criar a base de dados e o utilizador

Abre o **SQL Shell (psql)** que vem com o PostgreSQL (ou usa pgAdmin) e executa:

```sql
CREATE DATABASE kubuka_db;
CREATE USER kubuka_user WITH PASSWORD 'kubuka_pass';
GRANT ALL PRIVILEGES ON DATABASE kubuka_db TO kubuka_user;
ALTER USER kubuka_user CREATEDB;
```

> O `CREATEDB` é necessário para o Django poder criar a base de dados temporária dos testes.

Alternativa via linha de comandos:
```bash
psql -U postgres -c "CREATE DATABASE kubuka_db;"
psql -U postgres -c "CREATE USER kubuka_user WITH PASSWORD 'kubuka_pass';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE kubuka_db TO kubuka_user;"
psql -U postgres -c "ALTER USER kubuka_user CREATEDB;"
```

### Passo 9 — Criar o ficheiro .env

```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

Abre o ficheiro `.env` e substitui a `SECRET_KEY` por uma chave aleatória:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Cola o resultado no `.env`. As restantes variáveis já vêm preenchidas para desenvolvimento local.

### Passo 10 — Aplicar as migrações e criar o superutilizador

```bash
python manage.py migrate
python manage.py createsuperuser
```

Guarda o utilizador/palavra-passe que criares — vais precisar para aceder ao Django Admin.

### Passo 11 — Importar os workflows do n8n

Inicia o n8n numa janela separada:
```bash
n8n start
```

Acede a `http://localhost:5678` e cria a conta inicial.

Depois vai a **Workflows → Import from File** e importa os dois ficheiros da raiz do projecto:

| Ficheiro | O que faz |
|---|---|
| `n8n_workflow_kubuka.json` | Recebe o CV e devolve a análise |
| `n8n_workflow_job_scoring.json` | Compara candidato com vaga e devolve score |

**Activa cada workflow** com o toggle **Active** no canto superior direito.

### Passo 12 — Arrancar o sistema

```powershell
.\start.ps1
```

A aplicação fica disponível em **http://localhost:8000**.

Acede a `/signup/` para criar uma conta de candidato ou a `/signup/recruiter/` para uma conta de recrutador (fica pendente de aprovação — vai ao Django Admin para aprovar).

---

## Testes automatizados

Correr toda a suite (44 testes):

```bash
python manage.py test recruitment
```

**Testes end-to-end contra o Ollama real** (dentro de `scripts/`):

| Script | O que faz |
|---|---|
| `scripts/test_end_to_end.py` | Análise de CV + scoring de candidatura em sequência |
| `scripts/test_n8n_flow.py` | Só análise de CV |
| `scripts/test_scoring_flow.py` | Só scoring de candidatura |

Executar (com os serviços a correr):
```bash
python scripts/test_end_to_end.py
```

**Manutenção dos workflows n8n:**

Se precisares de reinstalar os workflows na BD do n8n (por exemplo depois de mudar de PC):
```bash
python scripts/update_n8n_workflows.py
```
Este script escreve directamente na SQLite do n8n (`~\.n8n\database.sqlite`) — o n8n tem de estar **parado** antes de o correres.

---

## Deploy em produção

O KUBUKA está preparado para correr atrás de **gunicorn** com estáticos servidos
por **WhiteNoise** (sem precisar de nginx só para isso), num container Docker.

### Com Docker (recomendado)

```bash
cp .env.example .env
# edita o .env: DEBUG=False, SECRET_KEY forte, ALLOWED_HOSTS e
# CSRF_TRUSTED_ORIGINS com o domínio real, N8N_*/DJANGO_BASE_URL a apontar
# para onde o n8n estiver acessível a partir do container.

docker compose up --build -d
```

O `docker-compose.yml` sobe o Django (gunicorn) e uma base PostgreSQL. O
`entrypoint.sh` aplica `migrate` e `collectstatic` automaticamente a cada
arranque. O n8n e o Ollama continuam self-hosted fora do compose, tal como no
desenvolvimento local — só é preciso garantir que o container consegue
alcançar os URLs definidos em `N8N_WEBHOOK_CV_URL` / `N8N_WEBHOOK_SCORE_URL`.

### Sem Docker (gunicorn directo)

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

### O que muda automaticamente com `DEBUG=False`

Definir `DEBUG=False` no `.env` liga sozinho, sem tocar em código: redireccionamento
para HTTPS, cookies de sessão/CSRF marcados `Secure`, HSTS, e o storage de
estáticos comprimidos do WhiteNoise. Ver o bloco "Checklist de produção" no
`.env.example` para a lista completa e como desligar algum item individualmente
(por exemplo, no primeiro deploy antes de haver certificado HTTPS válido).

### Observabilidade

- `GET /healthz/` — verifica a ligação à base de dados, devolve `200`/`503` em JSON.
- Logs em `logs/kubuka.log` (rotação automática a cada 5 MB, 5 ficheiros).
  Nível controlado por `DJANGO_LOG_LEVEL` no `.env` (por omissão `INFO`).

### Integração contínua

Cada push/PR para `main` corre lint (`ruff`) e a suite de 44 testes via GitHub
Actions (`.github/workflows/ci.yml`) — ver badge no topo deste README.

---

## Estrutura do projecto

```
kubuka/
├── core/                             — configuração Django
│   ├── settings.py
│   └── urls.py
├── recruitment/                      — aplicação principal
│   ├── models.py                     — User, Resume, Job, Application, Notification, AuditLog
│   ├── views.py                      — views HTML (candidatos e recrutadores)
│   ├── api_views.py                  — endpoints REST
│   ├── callback_views.py             — callbacks recebidos do n8n
│   ├── ai_service.py                 — envia pedidos para o n8n
│   ├── cv_processor.py               — extracção de texto do PDF
│   ├── notifications.py              — notificações in-app e email
│   ├── rate_limit.py                 — rate limiting
│   ├── tests.py                      — 44 testes
│   ├── migrations/
│   └── templates/                    — HTML com Tailwind + Flowbite
├── scripts/                          — scripts utilitários e testes end-to-end
│   ├── update_n8n_workflows.py       — reinstalar workflows na SQLite do n8n
│   ├── test_end_to_end.py            — teste CV + scoring
│   ├── test_n8n_flow.py              — só CV
│   └── test_scoring_flow.py          — só scoring
├── n8n_workflow_kubuka.json          — workflow de análise de CV
├── n8n_workflow_job_scoring.json     — workflow de scoring
├── start.ps1                         — script de arranque (Windows)
├── run_project.bat                   — duplo clique para arrancar
├── install_ocr_dependencies.py       — helper para instalar Tesseract/Poppler
├── .github/workflows/ci.yml          — lint + testes em cada push/PR
├── Dockerfile / docker-compose.yml   — imagem e stack de produção
├── entrypoint.sh                     — migrate + collectstatic + gunicorn
├── manage.py
├── requirements.txt / requirements-dev.txt
├── pyproject.toml                    — configuração do ruff (lint)
├── .env.example
├── CLAUDE.md                         — contexto do projecto (para IA)
├── SECURITY_REPORT.md                — relatório de segurança
├── CHANGELOG.md
└── README.md
```

---

## Problemas frequentes

### PostgreSQL não está a correr

O `start.ps1` avisa se a porta 5432 não estiver aberta. Para resolver de vez, configura o serviço como **automático** (ver Passo 2 acima).

Para verificar o estado:
```powershell
Get-Service | Where-Object { $_.DisplayName -like "*postgresql*" }
```

### O Ollama demora imenso a responder na primeira chamada

Na primeira chamada, o Ollama tem de carregar o modelo (~2 GB) do disco para a memória — isto pode demorar 1-5 minutos dependendo do disco/RAM. Chamadas seguintes são rápidas enquanto o modelo estiver carregado (por defeito 5 min).

Se o teu computador tem pouca RAM, podes forçar o Ollama a manter o modelo carregado mais tempo enviando `keep_alive` no pedido (já está configurado nos workflows).

### n8n devolve timeout ao chamar o Ollama

Sinal de que o modelo não está a caber em memória ou o CPU está sobrecarregado. Verifica RAM livre:
```powershell
(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB
# resultado em GB - precisa de pelo menos 2 GB livres
```

Alternativa temporária: em `scripts/update_n8n_workflows.py` muda o modelo do CV para `llama3.2:1b` (mais leve) e volta a correr o script.

### n8n não reage aos webhooks depois de importar os workflows

Certifica-te de que **activaste** cada workflow (toggle **Active** no canto superior direito de cada um). Workflows inactivos ignoram webhooks.

Se ainda assim não funcionar, clica no nó **Webhook** — o n8n mostra o URL de produção que deve corresponder ao valor no `.env`.

### Conta bloqueada após tentativas de login falhadas

O django-axes bloqueia após 5 tentativas erradas:
```bash
python manage.py axes_reset
# ou para um utilizador específico:
python manage.py axes_reset_user <username>
```

### `localhost` vs `127.0.0.1` no Windows

No Windows, o Node.js (n8n) resolve `localhost` como `::1` (IPv6), mas o Django e o Ollama ouvem em `127.0.0.1` (IPv4). Regra prática:
- Nos URLs do n8n dentro do `.env`: sempre `127.0.0.1`
- No `DJANGO_BASE_URL`: sempre `127.0.0.1`
- Dentro dos workflows n8n (que já vêm configurados): `http://127.0.0.1:11434` para o Ollama e `http://127.0.0.1:8000` para o Django

### Callback do n8n dá 403

Verifica que o header `X-Kubuka-Secret` nos nós HTTP dos workflows corresponde ao `N8N_CALLBACK_SECRET` no `.env`. Se mudares o secret, tens de o mudar nos dois lados.

---

## Contas de teste

| URL | O que faz |
|---|---|
| `/signup/` | Criar conta de candidato |
| `/signup/recruiter/` | Registar conta de recrutador (fica pendente de aprovação) |
| `/admin/` | Django Admin — gestão completa |

Para aprovar um recrutador: **Django Admin → Users → seleccionar o utilizador → activar `is_recruiter` e `recruiter_approved`**.
