"""Dati SINTETICI di sviluppo: python -m api.seed

Nomi, comuni e protocolli sono inventati. Rifiuta di girare fuori da
ESPOSTI_AMBIENTE=sviluppo. Ripetibile: se i dati ci sono già, non fa nulla.
"""
import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_sessionmaker
from .enums import Canale, Ruolo, Stato
from .models import CambioStato, Pratica, Ufficio, Utente
from .numerazione import prossimo_numero
from .registro import registra
from .security import hash_password

PASSWORD_SVILUPPO = os.environ.get("ESPOSTI_SEED_PASSWORD", "password-sintetica-1")


def esegui(db: Session) -> bool:
    if db.execute(select(Ufficio).where(Ufficio.codice == "VET")).scalar_one_or_none():
        return False
    vet = Ufficio(codice="VET", nome="Medicina Veterinaria")
    igp = Ufficio(codice="IGP", nome="Igiene pubblica")
    db.add_all([vet, igp])
    db.flush()
    h = hash_password(PASSWORD_SVILUPPO)
    for username, nome, ruolo, uff in [
        ("smistatore", "Sara Smistatrice (sintetica)", Ruolo.smistatore, None),
        ("op.vet", "Vittorio Veterinari (sintetico)", Ruolo.operatore, vet),
        ("op.igp", "Irene Igiene (sintetica)", Ruolo.operatore, igp),
        ("admin", "Amedeo Admin (sintetico)", Ruolo.amministratore, None),
    ]:
        db.add(Utente(username=username, nome_visualizzato=nome, ruolo=ruolo,
                      ufficio_id=uff.id if uff else None, password_hash=h))
    casi = [
        ("Pollaio a ridosso del confine", "Castelrovo", "0005120/2025", Stato.DA_SMISTARE, None),
        ("Cinque cani in un recinto senza riparo", "Borgoverde", "0004512/2025", Stato.DA_SMISTARE, None),
        ("Odori da allevamento", "Castelrovo", "0004890/2025", Stato.DA_VALIDARE, vet),
        ("Colonia felina in cortile", "Borgoverde", "0004101/2025", Stato.DA_VALIDARE, vet),
        ("Rumori notturni da laboratorio", "Pievalta", "0003990/2025", Stato.DA_VALIDARE, igp),
        ("Gatti in un'abitazione", "Pievalta", "0003177/2025", Stato.IN_LAVORAZIONE, vet),
        ("Cane alla catena (riscontro)", "Borgoverde", "0003177/2025", Stato.CHIUSA, vet),
        ("Documento in analisi", None, None, Stato.IN_ANALISI, None),
    ]
    for titolo, comune, prot, stato, uff in casi:
        p = Pratica(numero=prossimo_numero(db), protocollo=prot, tipo="esposto", titolo=titolo, comune=comune,
                    canale=Canale.caricamento_manuale, stato=stato, ufficio_id=uff.id if uff else None)
        db.add(p)
        db.flush()
        db.add(CambioStato(pratica_id=p.id, da_stato=None, a_stato=Stato.IN_ANALISI, utente_id=None))
        registra(db, utente_id=None, azione="pratica.crea", oggetto_tipo="pratica", oggetto_id=p.id,
                 pratica_id=p.id, dettagli={"origine": "seed_sintetico"})
    db.commit()
    return True


if __name__ == "__main__":
    if get_settings().ambiente != "sviluppo":
        raise SystemExit("Il seed sintetico gira solo con ESPOSTI_AMBIENTE=sviluppo")
    with get_sessionmaker()() as s:
        print("Dati sintetici creati." if esegui(s) else "Dati sintetici già presenti.")
