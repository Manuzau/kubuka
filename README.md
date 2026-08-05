# KUBUKA — Sistema de Pré-Selecção Inteligente de Candidatos

[![CI](https://github.com/Manuzau/kubuka/actions/workflows/ci.yml/badge.svg)](https://github.com/Manuzau/kubuka/actions/workflows/ci.yml)

O KUBUKA é um sistema web que automatiza a triagem de candidatos em empresas angolanas. A ideia surgiu da necessidade de reduzir o tempo que os recrutadores passam a analisar currículos manualmente — o sistema usa IA local (Ollama) para ler cada CV, atribuir uma pontuação e comparar o perfil do candidato com os requisitos da vaga.

> Trabalho de Fim de Curso — Licenciatura em Informática, 2025/2026

---

## Índice

- [O que o sistema faz](#o-que-o-sistema-faz)
- [Tecnologias usadas](#tecnologias-usadas)
- [Como o sistema funciona](#como-o-sistema-funciona)
- [Inicialização do Sistema](#inicialização-do-sistema)
  - [Arranque rápido (dia-a-dia)](#arranque-rápido-dia-a-dia)
  - [Instalação de raiz num computador novo](#instalação-de-raiz-num-computador-novo)
  - [Verificação final](#verificação-final)
- [Testes automatizados](#testes-automatizados)
- [Deploy em produção](#deploy-em-produção)
- [Estrutura do projecto](#estrutura-do-projecto)
- [Problemas frequentes](#problemas-frequentes)
- [Reset do sistema (estado limpo)](#reset-do-sistema-estado-limpo)

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

## Inicialização do Sistema

O KUBUKA é composto por **quatro peças separadas**. Para o fluxo completo (upload de CV → análise por IA → candidatura → score) funcionar, todas têm de estar a correr ao mesmo tempo:

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  PostgreSQL  │    │    Ollama    │    │     n8n      │    │    Django    │
│  porta 5432  │    │ porta 11434  │    │  porta 5678  │    │  porta 8000  │
│              │    │              │    │              │    │              │
│  guarda os   │    │  IA local    │    │  automação — │    │  aplicação   │
│  dados       │    │  (análise    │    │  liga o      │    │  web — o que │
│  (users,     │    │  de CV e     │    │  Django ao   │    │  o utilizador│
│  vagas, CVs) │    │  scoring)    │    │  Ollama      │    │  vê          │
└──────▲───────┘    └──────▲───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │                   │
       │                   └───── n8n chama o Ollama e devolve  ────┘
       └── Django lê/escreve directamente ────  o resultado ao Django
```

- O **PostgreSQL** é indispensável — sem ele o Django nem arranca.
- O **n8n** e o **Ollama** só entram em acção quando um candidato submete um CV ou se candidata a uma vaga — o resto (login, listagem de vagas, dashboard, perfil) funciona mesmo que estejam desligados.
- Consegues sempre confirmar o estado de cada um pela porta: `5432` (PostgreSQL), `11434` (Ollama), `5678` (n8n), `8000` (Django).

**O que fazer agora:**

| A tua situação | O que seguir |
|---|---|
| Já correste o KUBUKA neste computador antes (tudo instalado) | [Arranque rápido (dia-a-dia)](#arranque-rápido-dia-a-dia) — 1 comando |
| Computador novo, nunca instalaste nada disto | [Instalação de raiz num computador novo](#instalação-de-raiz-num-computador-novo) — ± 30-45 min, a maior parte à espera de downloads (~4 GB no total: modelos de IA + PostgreSQL + Node.js) |

### Arranque rápido (dia-a-dia)

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

### Instalação de raiz num computador novo

> Assume-se que estás em **Windows 10/11**. Para Linux/macOS, adapta os comandos onde indicado.
> Segue os passos por ordem — cada um tem uma linha "✅ **Confirma:**" para saberes se correu bem antes de avançar.

#### Passo 1 — Instalar ferramentas base

| Ferramenta | Onde | Notas de instalação |
|---|---|---|
| **Python 3.10+** | https://www.python.org/downloads/ | Marca "Add Python to PATH" durante a instalação |
| **Git** | https://git-scm.com/download/win | Aceita as opções padrão |
| **PostgreSQL 14+** | https://www.postgresql.org/download/ | Guarda a palavra-passe do utilizador `postgres` — vais precisar dela no Passo 8 |
| **Node.js LTS** | https://nodejs.org/ | Necessário para o n8n |
| **Ollama** | https://ollama.com | IA local, ocupa ~200 MB antes dos modelos |

✅ **Confirma** que cada ferramenta ficou disponível na linha de comandos (abre um **novo** terminal primeiro, para carregar o PATH actualizado):
```powershell
python --version
git --version
node --version
ollama --version
```
Todos devem devolver um número de versão. Se algum der "comando não encontrado", reinicia o terminal (ou o computador) e tenta de novo antes de continuar.

**Opcional — apenas se precisares de OCR (PDFs digitalizados/fotografados):**
```powershell
# Requer Chocolatey (https://chocolatey.org/install) - instala-o primeiro se ainda não o tiveres:
# Set-ExecutionPolicy Bypass -Scope Process -Force; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
choco install tesseract poppler
```
Sem isto, CVs em PDF normal (texto seleccionável) continuam a funcionar perfeitamente — só PDFs digitalizados/scaneados é que precisam de OCR.

#### Passo 2 — Configurar o PostgreSQL para arrancar sempre

Por omissão, o serviço fica em arranque manual. Para que arranque sempre que ligares o computador (PowerShell como Administrador):

```powershell
Set-Service -Name "postgresql-x64-18" -StartupType Automatic
Start-Service -Name "postgresql-x64-18"
```

> Se a versão for diferente, ajusta o número. Para descobrir o nome exacto:
> ```powershell
> Get-Service | Where-Object { $_.DisplayName -like "*postgresql*" }
> ```

✅ **Confirma:**
```powershell
Get-Service | Where-Object { $_.DisplayName -like "*postgresql*" } | Select-Object Status, StartType
```
`Status` deve ser `Running` e `StartType` deve ser `Automatic`.

#### Passo 3 — Instalar o n8n globalmente

```bash
npm install -g n8n
```

✅ **Confirma:** `n8n --version` devolve um número de versão (ex: `1.6x.x`).

#### Passo 4 — Descarregar os modelos Ollama

O `start.ps1` faz isto automaticamente na primeira execução, mas se preferires fazê-lo já (total ~3.2 GB — reserva 10-15 min consoante a ligação):

```bash
ollama pull llama3.2:1b
ollama pull qwen2.5:3b
```

✅ **Confirma:** `ollama list` mostra os dois modelos.

#### Passo 5 — Clonar o repositório

```bash
git clone https://github.com/Manuzau/kubuka.git
cd kubuka
```

✅ **Confirma:** `dir` (ou `ls`) mostra `manage.py`, `core/`, `recruitment/` na pasta actual.

#### Passo 6 — Criar o ambiente virtual Python

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

✅ **Confirma:** o início da linha do terminal passa a mostrar `(.venv)`.

#### Passo 7 — Instalar dependências Python

```bash
pip install -r requirements.txt
```

✅ **Confirma:** termina sem erros e `pip show django` mostra a versão instalada.

#### Passo 8 — Criar a base de dados e o utilizador

**Opção A — sabes a palavra-passe do utilizador `postgres`** (a que definiste ao instalar o PostgreSQL no Passo 1):

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

**Opção B — não sabes/esqueceste a palavra-passe do `postgres`:** corre o script incluído no projecto, numa PowerShell aberta **como Administrador** (botão direito → "Executar como administrador"). Ele repõe a password do `postgres` e cria a base/utilizador do KUBUKA automaticamente:
```powershell
.\scripts\setup_postgres.ps1
```
Vai pedir-te para definires uma nova palavra-passe para o `postgres` e trata do resto sozinho (ver comentário no topo do ficheiro para detalhes do que faz).

✅ **Confirma:**
```bash
psql -U kubuka_user -h 127.0.0.1 -d kubuka_db -c "SELECT current_user;"
```
Deve pedir a password (`kubuka_pass`, se não a mudaste) e devolver `kubuka_user`.

#### Passo 9 — Criar o ficheiro .env

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

✅ **Confirma:** `.env` existe na pasta do projecto e a linha `SECRET_KEY=` já não tem o valor de exemplo `cola-aqui-uma-chave-longa-e-aleatoria`.

#### Passo 10 — Aplicar as migrações e criar o superutilizador

```bash
python manage.py migrate
python manage.py createsuperuser
```

Guarda o utilizador/palavra-passe que criares — vais precisar para aceder ao Django Admin.

✅ **Confirma:** `migrate` termina com várias linhas `Applying recruitment.000X_...OK` e sem erros; o `createsuperuser` pede username/email/password e confirma a criação.

#### Passo 11 — Importar os workflows do n8n

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

✅ **Confirma:** os dois workflows aparecem na lista principal do n8n com o toggle **Active** a verde.

Podes fechar esta janela do n8n — o `start.ps1` (próximo passo) volta a abri-lo sozinho sempre que precisar.

#### Passo 12 — Arrancar o sistema

```powershell
.\start.ps1
```

Este é o mesmo comando do [Arranque rápido](#arranque-rápido-dia-a-dia) — a partir de agora, é o único comando que precisas para iniciar o KUBUKA neste computador. Segue a [Verificação final](#verificação-final) abaixo para confirmares que ficou tudo a funcionar.

---

### Verificação final

Depois do `start.ps1` terminar (a última linha deve ser `A iniciar Django...`), confirma que cada peça está mesmo a responder:

| # | O que verificar | Como | Resultado esperado |
|---|---|---|---|
| 1 | Django | Abre `http://localhost:8000` no browser | A página inicial do KUBUKA carrega |
| 2 | Health-check | Abre `http://localhost:8000/healthz/` | `{"status": "ok", "checks": {"database": "ok"}}` |
| 3 | n8n | Abre `http://localhost:5678` | O painel de workflows do n8n, com os 2 workflows **Active** |
| 4 | Ollama | Abre `http://localhost:11434` | A mensagem de texto simples `Ollama is running` |
| 5 | Registo | Acede a `/signup/` e cria uma conta de candidato | Conta criada, sessão iniciada automaticamente |
| 6 | Upload + IA | Com a conta de candidato, submete um CV em PDF em `/upload/` | Ao fim de alguns segundos/minutos (1ª chamada ao Ollama é mais lenta — ver [Problemas frequentes](#problemas-frequentes)), o CV aparece analisado com pontuação, competências, resumo, etc. |
| 7 | Django Admin | Acede a `/admin/` com o superutilizador do Passo 10 | Painel de administração do Django |

Se algum destes falhar, o mais provável é a causa estar coberta em [Problemas frequentes](#problemas-frequentes) — a secção está organizada exactamente por sintoma (PostgreSQL, Ollama lento, timeout do n8n, etc.).

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
│   ├── setup_postgres.ps1            — repõe a password do postgres e cria a BD/utilizador do KUBUKA
│   ├── update_n8n_workflows.py       — reinstalar workflows na SQLite do n8n
│   ├── n8n_workflow_kubuka.json      — workflow de análise de CV (importação manual)
│   ├── n8n_workflow_job_scoring.json — workflow de scoring (importação manual)
│   ├── generate_diagrams.py          — gera diagramas UML/DFD do TFC
│   ├── install_ocr_dependencies.py   — helper para instalar Tesseract/Poppler
│   ├── test_end_to_end.py            — teste CV + scoring
│   ├── test_n8n_flow.py              — só CV
│   └── test_scoring_flow.py          — só scoring
├── start.ps1                         — script de arranque (Windows)
├── run_project.bat                   — duplo clique para arrancar
├── .github/workflows/ci.yml          — lint + testes em cada push/PR
├── Dockerfile / docker-compose.yml   — imagem e stack de produção
├── entrypoint.sh                     — migrate + collectstatic + gunicorn
├── manage.py
├── requirements.txt / requirements-dev.txt
├── pyproject.toml                    — configuração do ruff (lint)
├── .env.example
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

---

## Reset do sistema (estado limpo)

Para apagar todos os dados de teste e voltar a um estado limpo — útil antes de validar a
solução com CVs reais/anonimizados, sem ruído de dados simulados:

```bash
python manage.py reset_sistema
```

O comando:
1. Recusa-se a correr se `DEBUG=False` ou se a base de dados não for local (protecção
   contra execução acidental em produção).
2. Pede confirmação (escrever o nome da base de dados) antes de apagar seja o que for.
3. Cria um backup (`pg_dump`, ou cópia do ficheiro em SQLite) em `backups/` com timestamp.
4. Faz `DROP`/`CREATE` da base de dados e corre `migrate` de raiz (as migrações em si
   não são alteradas nem apagadas).
5. Apaga os CVs em `media/resumes/` (mantém a pasta).
6. Cria um superutilizador único, para poderes entrar no `/admin/` e aprovar recrutadores
   a partir do zero.

**Flags:**

| Flag | Efeito |
|---|---|
| `--no-input` | Sem confirmação interactiva (scripts/CI) |
| `--keep-media` | Não apaga os CVs em `media/resumes/` |
| `--no-superuser` | Não cria o superutilizador no final |

**Credenciais do superutilizador** (variáveis de ambiente, com omissões sensatas se não
definidas): `DJANGO_SUPERUSER_USERNAME` (omissão `admin`), `DJANGO_SUPERUSER_EMAIL`
(omissão `admin@kubuka.local`), `DJANGO_SUPERUSER_PASSWORD` (omissão `Kubuka#Demo2026`).

Não mexe nos workflows do n8n nem no histórico de execuções, nem em `static/`/`staticfiles/`.
