#!/usr/bin/env bash
# Rigenera lo schema OpenAPI dal backend e i tipi TypeScript del backoffice, tutto in Docker:
#   frontend/backoffice/openapi.json  e  frontend/backoffice/src/api/schema.d.ts
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose build --quiet api backoffice
FE="$PWD/frontend/backoffice"
docker run --rm -u "$(id -u):$(id -g)" -v "$FE:/out" esposti-backend:dev \
  python -m api.esporta_openapi /out/openapi.json
docker run --rm -u "$(id -u):$(id -g)" -v "$FE/openapi.json:/app/openapi.json:ro" -v "$FE/src/api:/app/src/api" \
  esposti-backoffice:dev npm run --silent gen:api
echo "Aggiornati: frontend/backoffice/openapi.json, frontend/backoffice/src/api/schema.d.ts"
