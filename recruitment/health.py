"""Endpoint de health-check para orquestradores/monitorização (Docker, uptime checks, etc.).

Isolado dos restantes ficheiros da app para não interferir com views.py.
"""
from django.db import connection
from django.db.utils import OperationalError
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health_check(request):
    checks = {}

    try:
        connection.ensure_connection()
        checks['database'] = 'ok'
    except OperationalError as exc:
        checks['database'] = f'error: {exc}'

    healthy = all(value == 'ok' for value in checks.values())
    status_code = 200 if healthy else 503
    return JsonResponse(
        {'status': 'ok' if healthy else 'degraded', 'checks': checks},
        status=status_code,
    )
