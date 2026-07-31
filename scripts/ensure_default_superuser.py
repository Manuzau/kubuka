"""Garante que existe pelo menos um superutilizador, para a app ficar sempre acessível
em /admin/ sem passos manuais numa máquina nova (usado pelo start.ps1).

Idempotente: só cria a conta por omissão se NENHUM superutilizador existir ainda -
nunca mexe em contas já criadas manualmente (createsuperuser, Django Admin, etc.).
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import django  # noqa: E402

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from recruitment.models import User  # noqa: E402

DEFAULT_USERNAME = 'admin'
DEFAULT_EMAIL = 'admin@kubuka.local'
DEFAULT_PASSWORD = 'Kubuka#Demo2026'

if User.objects.filter(is_superuser=True).exists():
    print('EXISTS')
else:
    User.objects.create_superuser(DEFAULT_USERNAME, DEFAULT_EMAIL, DEFAULT_PASSWORD)
    print('CREATED')
