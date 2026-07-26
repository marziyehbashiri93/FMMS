#!/bin/sh
# Demo backend: Postgres data + no Redis/Celery worker.
set -eu

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.demo}"

# Neutralize Redis/Celery broker even if .env injects them.
export REDIS_URL="${REDIS_URL:-}"
export CELERY_BROKER_URL="memory://"

: "${POSTGRES_HOST:?POSTGRES_HOST is required (e.g. host.docker.internal or db)}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${POSTGRES_PORT:=5432}"

echo "FMMS demo: settings=${DJANGO_SETTINGS_MODULE}"
echo "FMMS demo: postgres=${POSTGRES_USER}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
echo "FMMS demo: cache=LocMem, celery=eager (no Redis)"

python manage.py migrate --noinput

exec python manage.py runserver 0.0.0.0:8000
