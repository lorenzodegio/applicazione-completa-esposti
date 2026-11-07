#!/usr/bin/env bash
# Rigenera i documenti SINTETICI del collaudo manuale in docs/collaudo/dati/ (contenuti inventati).
# Container usa e getta: le librerie si installano solo lì, niente sull'host.
set -euo pipefail
cd "$(dirname "$0")/.."
docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD/docs/collaudo/dati":/dati -w /dati python:3.12-slim \
  sh -c "pip install -q --disable-pip-version-check --root-user-action=ignore --target /tmp/lib reportlab==4.2.5 python-docx==1.1.2 pillow==11.0.0 \
         && PYTHONPATH=/tmp/lib python genera.py"
