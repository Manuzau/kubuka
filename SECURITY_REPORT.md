# Relatório de Segurança — KUBUKA

---

## Resumo 

Foram identificadas e corrigidas **13 vulnerabilidades** em 8 ficheiros do projecto, com criação de 2 novos ficheiros. O sistema passou de um estado com falhas críticas exploráveis (callbacks sem autenticação real, qualquer ficheiro aceite no upload) para um estado com defesa em profundidade adequada para um ambiente de desenvolvimento/TFC.

---

## Vulnerabilidades Corrigidas

### 🔴 CRÍTICO

#### SEC-01 — `_verify_secret()` aceitava pedidos sem token configurado
- **Ficheiro:** `recruitment/callback_views.py`
- **Problema:** Lógica `if expected and received != expected` retornava `True` quando `N8N_CALLBACK_SECRET` estava vazio. Qualquer pessoa podia chamar `/api/resume/<id>/ai-result/` e alterar scores de CVs.
- **Correcção:** Princípio de "fail-closed" — se o secret não estiver configurado, o acesso é negado e o erro é registado. Substituído por `hmac.compare_digest()` para comparação em tempo constante (previne timing attacks).
```python
# Antes (VULNERÁVEL):
if expected and received != expected:
    return False
return True

# Depois (SEGURO):
if not expected:
    logger.error("[security] N8N_CALLBACK_SECRET não configurado — bloqueado.")
    return False
return hmac.compare_digest(expected, received)
```

#### SEC-02 — Upload de CV sem validação de tipo ou tamanho
- **Ficheiro:** `recruitment/forms.py`
- **Problema:** `ResumeUploadForm` aceitava qualquer tipo de ficheiro. Potencial upload de ficheiros maliciosos (HTML, executáveis).
- **Correcção:** Validação de extensão (`.pdf`), MIME type (`application/pdf`) e tamanho máximo (5 MB) no método `clean_file()`.

---

### 🟠 MÉDIO

#### SEC-03 — Recrutador podia alterar candidaturas de outros recrutadores
- **Ficheiros:** `recruitment/views.py`, `recruitment/callback_views.py`, `recruitment/api_views.py`
- **Problema:** Qualquer recrutador autenticado podia mudar o estado de candidaturas de vagas criadas por outros recrutadores, passando um `pk` arbitrário.
- **Correcção:** Verificação de ownership adicionada nos três pontos de entrada:
  - `application_update_status_view` (views.py)
  - `application_update_status` (callback_views.py)
  - `ApplicationStatusView` e `RecruiterNotesView` (api_views.py)

#### SEC-04 — Recrutador podia activar/desactivar vagas de outros
- **Ficheiro:** `recruitment/views.py` — `job_toggle_active`
- **Problema:** `get_object_or_404(Job, pk=pk)` sem filtro de ownership.
- **Correcção:** Recrutadores usam `get_object_or_404(Job, pk=pk, created_by=request.user)`; administradores mantêm acesso total.

#### SEC-05 — Registo de recrutador sem aprovação de admin
- **Ficheiros:** `recruitment/views.py`, `recruitment/models.py`, `recruitment/admin.py`
- **Problema:** Qualquer pessoa podia registar-se como recrutador e aceder imediatamente ao dashboard com dados de todos os candidatos.
- **Correcção:** Adicionado campo `recruiter_approved` ao modelo `User` (default `True` para contas existentes). `RecruiterSignupView` define `recruiter_approved=False`. Todas as views de recrutador verificam a aprovação. Admin tem acções rápidas "Aprovar/Revogar recrutadores".

#### SEC-06 — `@csrf_exempt` em endpoint autenticado por sessão
- **Ficheiro:** `recruitment/callback_views.py` — `application_update_status`
- **Problema:** O endpoint verificava `request.user.is_authenticated` (autenticação por sessão) mas tinha `@csrf_exempt`, tornando a protecção CSRF inútil.
- **Correcção:** Removido `@csrf_exempt`. Pedidos da interface web (que usam sessão) requerem agora o token CSRF.

#### SEC-07 — Sem rate limiting no login (força bruta)
- **Ficheiros:** `core/settings.py`, `requirements.txt`
- **Correcção:** Instalado `django-axes 8.3.1`. Configuração: bloqueio após 5 tentativas falhadas, cooldown de 1 hora, reset do contador em login bem-sucedido. Middleware e backend integrados.

#### SEC-08 — Sem rate limiting no upload de CV (DoS)
- **Ficheiros:** `recruitment/rate_limit.py` (novo), `recruitment/views.py`
- **Problema:** Upload ilimitado accionava OCR + chamadas ao n8n em loop.
- **Correcção:** Criado módulo `rate_limit.py` com decorador cache-based. Upload limitado a 5 pedidos/minuto por utilizador.

---

### 🟡 MENOR

#### SEC-09 — `SECRET_KEY` com valor default inseguro conhecido
- **Ficheiro:** `core/settings.py`
- **Correcção:** Default alterado de `'django-insecure-default-key-for-dev'` para `'django-insecure-CHANGE-ME-before-production'`. Mensagem mais clara sobre a obrigatoriedade de alterar em produção.

#### SEC-10 — `ALLOWED_HOSTS` com wildcard `['*']` por default
- **Ficheiro:** `core/settings.py`
- **Correcção:** Default alterado para `['localhost', '127.0.0.1']`. Previne HTTP Host Header attacks em casos onde o `.env` não existe.

#### SEC-11 — `DEBUG=True` por default
- **Ficheiro:** `core/settings.py`
- **Correcção:** Default alterado para `False`. Debug deve ser activado explicitamente no `.env`.

#### SEC-12 — Sem cabeçalhos de segurança HTTP
- **Ficheiro:** `core/settings.py`
- **Correcção:** Adicionados:
  - `SECURE_CONTENT_TYPE_NOSNIFF = True` — previne MIME sniffing
  - `SECURE_BROWSER_XSS_FILTER = True` — protecção XSS em browsers antigos
  - `X_FRAME_OPTIONS = 'DENY'` — protecção contra clickjacking (reforça o middleware já existente)
  - `FILE_UPLOAD_MAX_MEMORY_SIZE = 5 MB` — limite de upload em memória
  - `DATA_UPLOAD_MAX_MEMORY_SIZE = 6 MB` — limite total por pedido

#### SEC-13 — Exportação CSV sem registo de auditoria
- **Ficheiros:** `recruitment/models.py`, `recruitment/views.py`, `recruitment/admin.py`
- **Problema:** Exportação de dados pessoais (emails, nomes) sem qualquer log. Relevante para conformidade com legislação de protecção de dados.
- **Correcção:** Criado modelo `AuditLog` para registar exportações CSV, alterações de estado de candidaturas e toggles de vagas. Painel dedicado no Django Admin (só leitura; só superutilizadores podem eliminar).

---

## Ficheiros Modificados

| Ficheiro | Tipo de Alteração |
|---|---|
| `recruitment/callback_views.py` | Fix `_verify_secret`, `hmac.compare_digest`, ownership check, remoção `@csrf_exempt` |
| `recruitment/forms.py` | Validação de tipo (PDF), MIME type e tamanho (5 MB) |
| `recruitment/models.py` | Campo `User.recruiter_approved`, modelo `AuditLog` |
| `recruitment/views.py` | Rate limit no upload, ownership checks, audit log, verificação `recruiter_approved` |
| `recruitment/api_views.py` | Ownership checks, remoção import não usado, `recruiter_approved` em `IsRecruiterOrAdmin` |
| `recruitment/admin.py` | Registo `AuditLog`, acções de aprovação de recrutadores |
| `core/settings.py` | Defaults seguros, cabeçalhos HTTP, limites de upload, configuração axes |
| `requirements.txt` | Adicionado `django-axes` |
| `.env.example` | Instruções de segurança para `SECRET_KEY` e `N8N_CALLBACK_SECRET` |

## Ficheiros Criados

| Ficheiro | Descrição |
|---|---|
| `recruitment/rate_limit.py` | Decorador de rate limiting baseado na cache do Django |
| `recruitment/migrations/0011_security_fields.py` | Migration para `recruiter_approved` e `AuditLog` |

---

## Verificação Pós-Implementação

```
python manage.py check → System check identified no issues (0 silenced).
python manage.py migrate → No migrations to apply. (tudo aplicado)
axes 8.3.1 instalado e funcional
Migration 0011_security_fields aplicada com sucesso
```

---

## Recomendações para Produção (Não Implementadas)

Estas configurações requerem HTTPS e um domínio real — não aplicáveis em desenvolvimento local:

```python
SECURE_SSL_REDIRECT = True          # Redireciona HTTP → HTTPS
SESSION_COOKIE_SECURE = True        # Cookie de sessão só em HTTPS
CSRF_COOKIE_SECURE = True           # Cookie CSRF só em HTTPS
SECURE_HSTS_SECONDS = 31536000      # HTTP Strict Transport Security (1 ano)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
```

Está documentadas como comentário em `settings.py` para activação futura.

---

*KUBUKA — Relatório de Segurança — TFC 2025/2026*
