"""Percorso della pratica: non è una tabella, si calcola (piano 3.8)."""
import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from .analisi import stato_analisi_documento
from .collegamenti import collegate, id_visibili, riferimento
from .enums import Stato, StatoAttivita
from .models import Assegnazione, Attivita, Documento, Pratica, Ufficio, Utente, Valutazione
from .schemas import PassoPercorso
from .valutazione import ultimo_risultato_principale

TIPI_INOLTRO = {"inoltro_per_competenza": "Inoltro per competenza", "richiesta_ente": "Richiesta di un ente"}


def _giorno(d: dt.date) -> dt.datetime:
    return dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc)


def percorso(db: Session, utente: Utente, pratica: Pratica) -> list[PassoPercorso]:
    passi: list[PassoPercorso] = []
    docs = db.execute(select(Documento).where(Documento.pratica_id == pratica.id)
                      .order_by(Documento.caricato_il, Documento.id)).scalars().all()

    # Esposto
    esposto = next((d for d in docs if d.tipo_documento == "esposto"), None)
    if esposto is None and pratica.tipo == "esposto":
        esposto = next((d for d in docs if d.id == pratica.documento_principale_id), None)
    if esposto:
        passi.append(PassoPercorso(passo="esposto", stato="concluso", titolo="Esposto ricevuto",
                                   data=esposto.caricato_il, documento_id=esposto.id, pagina=1))
    # Inoltro (non mostrato se assente)
    for d in docs:
        if d.tipo_documento in TIPI_INOLTRO:
            passi.append(PassoPercorso(passo="inoltro", stato="concluso", titolo=TIPI_INOLTRO[d.tipo_documento],
                                       data=d.caricato_il, documento_id=d.id, pagina=1))
    # Proposta dell'IA
    if pratica.documento_principale_id:
        r = ultimo_risultato_principale(db, pratica.id)
        analisi = stato_analisi_documento(db, pratica.documento_principale_id)
        if analisi and analisi.stato == "in_corso" and r is None:
            passi.append(PassoPercorso(passo="proposta_ia", stato="in_corso", titolo="Analisi in corso"))
        elif r:
            passi.append(PassoPercorso(
                passo="proposta_ia", stato="concluso", titolo="Proposta dell'IA", data=r.ricevuto_il,
                testo=f"{r.proposta.get('esito')}, urgenza {r.proposta.get('urgenza')} (suggerimento)",
                documento_id=r.documento_id))
        elif analisi and analisi.stato == "non_disponibile":
            passi.append(PassoPercorso(passo="proposta_ia", stato="concluso", titolo="Analisi non disponibile"))
    # Smistamento
    for a in db.execute(select(Assegnazione).where(Assegnazione.pratica_id == pratica.id)
                        .order_by(Assegnazione.assegnata_il, Assegnazione.id)).scalars():
        uff = db.get(Ufficio, a.ufficio_id)
        passi.append(PassoPercorso(passo="smistamento", stato="concluso", data=a.assegnata_il, testo=a.motivo,
                                   titolo=f"{'Riassegnata' if a.ufficio_precedente_id else 'Assegnata'} a {uff.nome}"))
    if pratica.stato == Stato.DA_SMISTARE:
        passi.append(PassoPercorso(passo="smistamento", stato="atteso", titolo="Smistamento",
                                   testo="In attesa di assegnazione a un ufficio"))
    # Validazione
    v = db.execute(select(Valutazione).where(Valutazione.pratica_id == pratica.id)).scalar_one_or_none()
    if v and v.compilata:
        chi = v.autore_nome or (db.get(Utente, v.autore_id).nome_visualizzato if v.autore_id else None)
        passi.append(PassoPercorso(
            passo="validazione", stato="concluso", testo=f"Valutata da {chi}" if chi else None,
            titolo="Validazione" if v.origine.value == "applicazione" else "Valutazione ATS importata",
            data=_giorno(v.data_compilazione) if v.data_compilazione else v.aggiornata_il))
    elif pratica.stato == Stato.DA_VALIDARE:
        passi.append(PassoPercorso(passo="validazione", stato="atteso", titolo="Validazione",
                                   testo="In attesa della valutazione dell'operatore"))
    # Azioni
    mappa = {StatoAttivita.prevista: "atteso", StatoAttivita.in_corso: "in_corso", StatoAttivita.conclusa: "concluso"}
    for a in db.execute(select(Attivita).where(Attivita.pratica_id == pratica.id, Attivita.stato != StatoAttivita.annullata)
                        .order_by(Attivita.creata_il, Attivita.id)).scalars():
        giorno = a.data_conclusione or a.data_prevista
        passi.append(PassoPercorso(passo="azione", stato=mappa[a.stato], titolo=a.tipo, testo=a.descrizione,
                                   data=_giorno(giorno) if giorno else None))
    # Riscontro: atteso finché non arriva
    if pratica.tipo == "esposto" and pratica.stato in (Stato.DA_VALIDARE, Stato.IN_LAVORAZIONE, Stato.CHIUSA):
        trovati = [c for c in collegate(db, pratica) if c.pratica.tipo == "riscontro_ats"]
        if trovati:
            c = trovati[0]
            visibile = c.pratica.id in id_visibili(db, utente, [c.pratica.id])
            passi.append(PassoPercorso(passo="riscontro", stato="concluso", titolo="Riscontro ricevuto",
                                       data=c.pratica.creata_il, pratica_collegata=riferimento(c.pratica, visibile)))
        elif pratica.stato != Stato.CHIUSA:
            passi.append(PassoPercorso(passo="riscontro", stato="atteso", titolo="Riscontro",
                                       testo="In attesa del riscontro"))
    return passi
