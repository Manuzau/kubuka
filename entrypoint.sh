#!/bin/sh
set -e

echo "[entrypoint] A aplicar migrations..."
python manage.py migrate --noinput

echo "[entrypoint] A recolher ficheiros estáticos..."
python manage.py collectstatic --noinput

echo "[entrypoint] A arrancar gunicorn..."
exec gunicorn core.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --access-logfile - \
    --error-logfile -
