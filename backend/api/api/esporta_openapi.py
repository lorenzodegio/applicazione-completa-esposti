"""Scrive lo schema OpenAPI dell'API: da lì il frontend genera i tipi (npm run gen:api).

    PYTHONPATH=.. python -m api.esporta_openapi ../../frontend/backoffice/openapi.json
"""
import json
import sys

from .main import app

percorso = sys.argv[1] if len(sys.argv) > 1 else "openapi.json"
with open(percorso, "w", encoding="utf-8") as f:
    json.dump(app.openapi(), f, ensure_ascii=False, indent=2, sort_keys=True)
    f.write("\n")
print(f"Schema scritto in {percorso}")
