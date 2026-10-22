#!/usr/bin/env bash
# Prova di aggancio con il motore VERO (classificatore-esposti-v2), in un progetto compose separato e pulito.
# Prima, nel repository del motore:   docker compose up -d motore      (avvia anche Ollama)
# Poi, da qui:                         scripts/prova-motore-vero.sh
# Documenti: quelli SINTETICI del motore (MOTORE_DATI_SINTETICI, default ../classificatore-esposti-v2/tests/dati_sintetici).
# Usa la GPU (tramite il motore): una prova alla volta.
set -uo pipefail
cd "$(dirname "$0")/.."

compose() { docker compose -f compose.yml -f compose.motore-vero.yml --profile motore-vero -p esposti-aggancio "$@"; }

if ! docker network inspect esposti_interna >/dev/null 2>&1; then
  echo "Manca la rete esposti_interna: docker network create --internal esposti_interna"; exit 2
fi
if ! docker network inspect esposti_interna --format '{{range .Containers}}{{.Name}} {{end}}' | grep -q motore; then
  echo "Il motore vero non è sulla rete esposti_interna: avvialo nel suo repository (docker compose up -d motore)"; exit 2
fi

compose down -v --remove-orphans >/dev/null 2>&1
compose build --quiet || exit 1
esito=0
compose run --rm e2e-motore-vero || esito=$?
if [ "$esito" -ne 0 ]; then
  echo "--- ultime righe di api e worker ---"
  compose logs --no-color --tail 40 api worker
fi
compose down -v --remove-orphans >/dev/null 2>&1
echo "=== prova con il motore vero -> $([ "$esito" -eq 0 ] && echo OK || echo "FALLITA ($esito)") ==="
exit "$esito"
