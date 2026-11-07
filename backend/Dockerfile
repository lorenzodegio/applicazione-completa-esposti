# Immagine unica del backend: api, worker, finto motore e test (sorgenti dentro l'immagine).
# Le dipendenze si installano in build, dal pyproject: nessun pip all'avvio.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_ROOT_USER_ACTION=ignore \
    PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONPATH=/app/backend/api:/app/backend

WORKDIR /app/backend
COPY api/pyproject.toml api/pyproject.toml
# dipendenze dell'app + quelle dei test (pgserver no: nei container c'è il servizio db)
RUN python -c "import tomllib; p = tomllib.load(open('api/pyproject.toml', 'rb'))['project']; \
d = [x for x in p['dependencies'] + p['optional-dependencies']['dev'] if not x.startswith('pgserver')]; \
open('/tmp/requisiti.txt', 'w').write('\n'.join(d))" \
 && pip install -r /tmp/requisiti.txt && rm /tmp/requisiti.txt

COPY . .
# utente senza privilegi; /dati è il volume dell'archivio documenti
RUN useradd --create-home --uid 1000 esposti && mkdir -p /dati && chown esposti /dati
USER esposti
WORKDIR /app/backend/api
EXPOSE 8000 8080
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
