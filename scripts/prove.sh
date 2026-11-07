#!/usr/bin/env bash
# Tutte le prove in Docker, ognuna in un progetto compose separato e pulito (database su tmpfs,
# archivio nuovo, nessuna porta sull'host), che si cancella alla fine.
#
#   scripts/prove.sh              # tutte: backend, frontend, live, e2e
#   scripts/prove.sh backend      # pytest su PostgreSQL
#   scripts/prove.sh frontend     # typecheck + test unit (vitest, backend simulato)
#   scripts/prove.sh live         # vitest con l'app vera contro API + worker + finto motore
#   scripts/prove.sh e2e          # Playwright (Chromium) contro lo stack completo
set -uo pipefail
cd "$(dirname "$0")/.."

compose() { docker compose -f compose.yml -f compose.prove.yml --profile prove -p "$PROGETTO" "$@"; }

esegui() {
  local suite=$1 servizio=$2
  PROGETTO="esposti-prove-$suite"
  echo "=== prove: $suite (progetto $PROGETTO) ==="
  compose down -v --remove-orphans >/dev/null 2>&1
  compose build --quiet || return 1
  local esito=0
  compose run --rm "$servizio" || esito=$?
  if [ "$esito" -ne 0 ] && [ "$suite" = live -o "$suite" = e2e ]; then
    echo "--- ultime righe di api, worker e motore-finto ---"
    compose logs --no-color --tail 30 api worker motore-finto
  fi
  compose down -v --remove-orphans >/dev/null 2>&1
  echo "=== prove: $suite -> $([ "$esito" -eq 0 ] && echo OK || echo "FALLITE ($esito)") ==="
  return "$esito"
}

declare -A SERVIZIO=([backend]=test-backend [frontend]=test-frontend [live]=test-live [e2e]=e2e)
SUITE=("$@")
[ ${#SUITE[@]} -eq 0 ] && SUITE=(backend frontend live e2e)

fallite=()
for s in "${SUITE[@]}"; do
  [ -n "${SERVIZIO[$s]:-}" ] || { echo "suite sconosciuta: $s (backend|frontend|live|e2e)"; exit 2; }
  esegui "$s" "${SERVIZIO[$s]}" || fallite+=("$s")
done
if [ ${#fallite[@]} -gt 0 ]; then echo "FALLITE: ${fallite[*]}"; exit 1; fi
echo "Tutte le prove sono passate: ${SUITE[*]}"
