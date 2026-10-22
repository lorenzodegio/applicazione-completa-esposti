"""Controlla e ripara gli accessi demo: python -m api.accessi_demo [--ripara]

Senza opzioni è solo una diagnosi: dice quale database usa e, per ciascun utente demo,
se esiste, se è attivo e se la password demo funziona. Con --ripara:
  - database senza utenti demo → crea tutti i dati demo (come `python -m api.demo`);
  - utenti presenti ma disattivati o con un'altra password → riattiva e rimette la password demo.
Solo con ESPOSTI_AMBIENTE=sviluppo. Le password demo sono dati sintetici.
"""
import sys

from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_sessionmaker
from .models import Pratica, Utente
from .registro import registra
from .security import hash_password, verifica_password
from .seed import PASSWORD_SVILUPPO

UTENTI_DEMO = ["smistatore", "op.vet", "op.igp", "admin"]


def diagnosi(db: Session) -> dict[str, dict]:
    """Per ogni utente demo: {'esiste', 'attivo', 'password_ok'}."""
    out = {}
    for nome in UTENTI_DEMO:
        u = db.execute(select(Utente).where(Utente.username == nome)).scalar_one_or_none()
        out[nome] = {"esiste": u is not None, "attivo": bool(u and u.attivo),
                     "password_ok": bool(u and verifica_password(u.password_hash, PASSWORD_SVILUPPO))}
    return out


def ripara(db: Session) -> list[str]:
    """Riattiva e rimette la password demo agli utenti demo esistenti. Restituisce cosa ha fatto."""
    fatto = []
    for nome in UTENTI_DEMO:
        u = db.execute(select(Utente).where(Utente.username == nome)).scalar_one_or_none()
        if u is None:
            continue
        cambi = []
        if not u.attivo:
            u.attivo = True
            cambi.append("riattivato")
        if not verifica_password(u.password_hash, PASSWORD_SVILUPPO):
            u.password_hash = hash_password(PASSWORD_SVILUPPO)
            cambi.append("password rimessa")
        if cambi:
            registra(db, utente_id=None, azione="utente.password", oggetto_tipo="utente", oggetto_id=u.id,
                     dettagli={"origine": "accessi_demo", "cambi": cambi})
            fatto.append(f"{nome}: {', '.join(cambi)}")
    db.commit()
    return fatto


def _riga(nome: str, d: dict) -> str:
    if not d["esiste"]:
        return f"  {nome:<11} NON ESISTE nel database"
    esito = "password demo OK" if d["password_ok"] else "password DIVERSA da quella demo"
    return f"  {nome:<11} {'attivo' if d['attivo'] else 'DISATTIVATO':<12} {esito}"


def main() -> None:
    cfg = get_settings()
    if cfg.ambiente != "sviluppo":
        raise SystemExit("Solo con ESPOSTI_AMBIENTE=sviluppo")
    url = make_url(cfg.database_url)
    print(f"Database usato: {url.host or 'socket'}:{url.port or ''} / {url.database}  (utente {url.username})")
    with get_sessionmaker()() as db:
        n_utenti = db.execute(select(func.count()).select_from(Utente)).scalar_one()
        n_pratiche = db.execute(select(func.count()).select_from(Pratica)).scalar_one()
        print(f"Contiene {n_utenti} utenti e {n_pratiche} pratiche.\n")
        stato = diagnosi(db)
        for nome, d in stato.items():
            print(_riga(nome, d))
        nessuno = not any(d["esiste"] for d in stato.values())
        ok = all(d["esiste"] and d["attivo"] and d["password_ok"] for d in stato.values())
        print()
        if ok:
            print(f"Gli accessi demo sono a posto: password {PASSWORD_SVILUPPO}")
            print("Se il browser dice ancora 'Credenziali non valide', controlla di aver scritto la password")
            print("esattamente cosi' (o che il browser non abbia compilato un'altra password salvata).")
            return
        if "--ripara" not in sys.argv:
            print("Qualcosa non va. Per sistemarlo: lancia ripara-accessi.bat (o aggiungi --ripara).")
            raise SystemExit(1)
        if nessuno:
            print("Nel database non ci sono gli utenti demo: creo tutti i dati demo...")
            from .demo import main as crea_demo
            crea_demo()
        else:
            for riga in ripara(db) or ["nessun cambiamento necessario"]:
                print("  fatto -", riga)
        stato = diagnosi(db)
    print("\nSituazione dopo la riparazione:")
    for nome, d in stato.items():
        print(_riga(nome, d))
    if all(d["esiste"] and d["attivo"] and d["password_ok"] for d in stato.values()):
        print(f"\nOra puoi accedere con uno di questi utenti e password: {PASSWORD_SVILUPPO}")
    else:
        raise SystemExit("Qualche utente risulta ancora non a posto: incolla questo messaggio.")


if __name__ == "__main__":
    main()
