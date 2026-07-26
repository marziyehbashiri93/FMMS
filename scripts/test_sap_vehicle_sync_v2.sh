#!/bin/sh
# Build the demo v2 backend and run the real SAP vehicle sync command.
set -eu

if [ -f .env ]; then
    set -a
    . ./.env
    set +a
fi

: "${SAP_USERNAME:?SAP_USERNAME is required}"
: "${SAP_PASSWORD:?SAP_PASSWORD is required}"

COMPOSE_FILES="-f docker-compose.demo.yml -f docker-compose.sap-v2.yml"

docker compose ${COMPOSE_FILES} up --build -d backend
docker compose ${COMPOSE_FILES} exec backend python manage.py sync_sap_vehicles "$@"
