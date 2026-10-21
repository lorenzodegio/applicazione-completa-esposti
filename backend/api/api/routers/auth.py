import datetime as dt

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..deps import COOKIE_SESSIONE, utente_corrente
from ..enums import Provider, Ruolo
from ..models import RegistroAzioni, Sessione, Utente
from ..registro import registra
from ..schemas import LoginIn, MeOut
from ..security import hash_token, nuovo_token, verifica_password

router = APIRouter(prefix="/auth", tags=["accesso"])

MENU = {
    Ruolo.smistatore: ["Home", "Inbox", "Fascicoli", "Gestione pratiche", "Smistamento"],
    Ruolo.operatore: ["Home", "Inbox", "Fascicoli", "Gestione pratiche"],
    Ruolo.amministratore: ["Uffici", "Utenti"],
}


def _me(utente: Utente) -> MeOut:
    return MeOut(utente=utente, menu=MENU[utente.ruolo])


@router.post("/login", response_model=MeOut)
def login(dati: LoginIn, risposta: Response, db: Session = Depends(get_db)) -> MeOut:
    cfg = get_settings()
    ora = dt.datetime.now(dt.timezone.utc)
    finestra = ora - dt.timedelta(minutes=cfg.login_finestra_minuti)
    fallimenti = db.execute(
        select(func.count()).select_from(RegistroAzioni).where(
            RegistroAzioni.azione == "accesso.fallito",
            RegistroAzioni.quando >= finestra,
            RegistroAzioni.dettagli["username"].as_string() == dati.username,
        )
    ).scalar_one()
    if fallimenti >= cfg.login_max_tentativi:
        raise HTTPException(429, "Troppi tentativi: riprova più tardi")

    utente = db.execute(select(Utente).where(Utente.username == dati.username)).scalar_one_or_none()
    hash_ = utente.password_hash if utente and utente.provider == Provider.locale else None
    password_ok = verifica_password(hash_, dati.password)
    if not (utente and utente.attivo and password_ok):
        registra(db, utente_id=None, azione="accesso.fallito", oggetto_tipo="utente",
                 dettagli={"username": dati.username[:100]})
        db.commit()
        raise HTTPException(401, "Credenziali non valide")

    token = nuovo_token()
    db.add(Sessione(id=hash_token(token), utente_id=utente.id,
                    scade_il=ora + dt.timedelta(hours=cfg.sessione_durata_ore)))
    utente.ultimo_accesso = ora
    registra(db, utente_id=utente.id, azione="accesso.riuscito", oggetto_tipo="utente", oggetto_id=utente.id)
    db.commit()
    risposta.set_cookie(COOKIE_SESSIONE, token, httponly=True, secure=cfg.cookie_secure,
                        samesite="strict", max_age=cfg.sessione_durata_ore * 3600)
    return _me(utente)


@router.post("/logout", status_code=204)
def logout(
    risposta: Response,
    utente: Utente = Depends(utente_corrente),
    token: str | None = Cookie(default=None, alias=COOKIE_SESSIONE),
    db: Session = Depends(get_db),
) -> None:
    sessione = db.get(Sessione, hash_token(token or ""))
    if sessione:
        sessione.revocata = True
    registra(db, utente_id=utente.id, azione="accesso.logout", oggetto_tipo="utente", oggetto_id=utente.id)
    db.commit()
    risposta.delete_cookie(COOKIE_SESSIONE)


@router.get("/me", response_model=MeOut)
def me(utente: Utente = Depends(utente_corrente)) -> MeOut:
    return _me(utente)
