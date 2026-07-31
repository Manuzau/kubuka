# Changelog

Todas as alterações relevantes deste projecto são documentadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-PT/1.1.0/).

## [Unreleased]

### Adicionado
- Preparação para produção: `Dockerfile`, `docker-compose.yml` e `entrypoint.sh`
  (gunicorn + WhiteNoise, migrations e `collectstatic` automáticos no arranque).
- Cabeçalhos de segurança HTTPS (`SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`,
  `CSRF_COOKIE_SECURE`, HSTS) activados automaticamente quando `DEBUG=False`,
  sem exigir edição manual de `core/settings.py` antes de um deploy.
- Logging estruturado (`LOGGING` em `core/settings.py`): consola sempre activa
  e ficheiro rotativo em `logs/kubuka.log` para os loggers `django` e `recruitment`.
- Endpoint de health-check `GET /healthz/` (`recruitment/health.py`) para
  orquestradores e monitorização externa.
- Integração contínua (`.github/workflows/ci.yml`): lint com `ruff` e a suite
  de 44 testes automatizados em cada push/PR para `main`.
- `pyproject.toml` (configuração do `ruff`) e `.pre-commit-config.yaml`.
- `requirements-dev.txt` com dependências de desenvolvimento (`ruff`, `pre-commit`).

### Alterado
- `.env.example` documenta as novas variáveis (`CSRF_TRUSTED_ORIGINS`,
  `DJANGO_LOG_LEVEL`, `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT`) e a checklist de
  produção actualizada (a maioria já é automática via `DEBUG=False`).

Sem alterações à lógica de negócio (`models.py`, `views.py`, `api_views.py`,
`cv_processor.py`, `ai_service.py`) nem aos templates HTML.
