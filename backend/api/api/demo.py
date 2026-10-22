"""Ambiente di prova per lo sviluppo del frontend: python -m api.demo

Crea (se mancano) i dati sintetici del seed, carica documenti SINTETICI scelti per far
scattare i vari scenari del finto motore, li fa analizzare e ne assegna alcuni agli uffici,
così Inbox, Smistamento, Gestione pratiche e Fascicoli hanno contenuto.
Solo con ESPOSTI_AMBIENTE=sviluppo. Ripetibile: se c'è già, non rifà nulla.

I documenti della demo li analizza SEMPRE il finto motore nello stesso processo, anche se
ESPOSTI_MOTORE_URL punta al motore vero: sono file sintetici fatti per gli scenari del finto.
"""
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from motore.client import motore_finto_in_processo

from .config import get_settings
from .db import get_sessionmaker
from .main import app
from .models import Pratica, Ufficio
from .seed import PASSWORD_SVILUPPO, esegui as seed
from .worker import esegui_coda

# (nome file → scenario del finto motore, ufficio a cui assegnare: None = resta da smistare)
CASI = [
    ("esposto_cani_via_robinie.pdf", "VET"),
    ("foglio_manoscritto_pollaio.pdf", "VET"),
    ("esposto_gatti_via_molino.pdf", "VET"),
    ("esposto_rumori_laboratorio.pdf", "IGP"),
    ("riscontro_ats_cane_catena.pdf", "VET"),
    ("lettera_ente.pages", None),
    ("esposto_cane_libero.pdf", None),
    ("esposto_instabile_esche.pdf", "VET"),
]


def main() -> None:
    if get_settings().ambiente != "sviluppo":
        raise SystemExit("La demo gira solo con ESPOSTI_AMBIENTE=sviluppo")
    with get_sessionmaker()() as db:
        seed(db)
        if db.execute(select(func.count()).select_from(Pratica).where(Pratica.titolo.like("%_demo"))).scalar_one():
            print("Demo già presente.")
            return
    c = TestClient(app, base_url="https://demo")
    assert c.post("/api/v1/auth/login", json={"username": "smistatore", "password": PASSWORD_SVILUPPO}).status_code == 200
    ids = []
    for nome, _ in CASI:
        r = c.post("/api/v1/pratiche", files=[("files", (nome, f"contenuto sintetico di {nome}".encode(), "application/pdf"))],
                   data={"titolo": nome.rsplit(".", 1)[0].replace("_", " ").capitalize() + "_demo"})
        ids.append(r.json()["pratica"]["id"])
    esegui_coda(client=motore_finto_in_processo(), dormi=lambda s: None)
    with get_sessionmaker()() as db:
        uffici = {u.codice: u for u in db.execute(select(Ufficio)).scalars()}
    for pid, (_, uff) in zip(ids, CASI):
        if uff:
            v = c.get(f"/api/v1/pratiche/{pid}").json()["versione"]
            r = c.post(f"/api/v1/pratiche/{pid}/assegnazione", json={"versione": v, "ufficio_id": str(uffici[uff].id)})
            assert r.status_code == 200, r.text
    print(f"Demo creata: {len(ids)} pratiche. Utenti: smistatore, op.vet, op.igp, admin (password: {PASSWORD_SVILUPPO})")


if __name__ == "__main__":
    main()
