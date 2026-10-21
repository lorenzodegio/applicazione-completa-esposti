import uuid

from fastapi import FastAPI, Request
from sqlalchemy import text

from .db import get_engine
from .registro import id_richiesta_corrente
from .routers import amministrazione, auth, collegamenti, documenti, operatore, pratiche, schermate

app = FastAPI(title="Gestione esposti — ATS Insubria", version="0.1.0")


@app.middleware("http")
async def id_richiesta(request: Request, call_next):
    rid = uuid.uuid4().hex
    token = id_richiesta_corrente.set(rid)
    try:
        risposta = await call_next(request)
    finally:
        id_richiesta_corrente.reset(token)
    risposta.headers["X-Request-Id"] = rid
    return risposta


# collegamenti prima di pratiche: /pratiche/ricerca-rapida non è un uuid
for r in (auth.router, collegamenti.router, pratiche.router, operatore.router, documenti.router, schermate.router,
          amministrazione.router):
    app.include_router(r, prefix="/api/v1")


@app.get("/api/v1/salute")
def salute() -> dict:
    # Archivio, coda e motore si aggiungono quando esistono (fasi 2 e 5).
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"database": "ok"}
    except Exception:
        return {"database": "errore"}
