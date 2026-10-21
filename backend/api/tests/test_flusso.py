"""Transizioni, assegnazione/restituzione, blocco ottimistico, registro."""
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from api.enums import Ruolo, Stato
from api.models import Pratica, RegistroAzioni
from api.transizioni import TRANSIZIONI

P = "/api/v1"


@pytest.fixture
def s(crea_ufficio, crea_utente):
    a = crea_ufficio()
    return dict(a=a, b=crea_ufficio(), smi=crea_utente(Ruolo.smistatore), op=crea_utente(Ruolo.operatore, a))


def azioni(db, pratica_id):
    return [r.azione for r in db.execute(
        select(RegistroAzioni).where(RegistroAzioni.pratica_id == pratica_id).order_by(RegistroAzioni.id)).scalars()]


# --- tabella delle transizioni ----------------------------------------------------

def test_stati_non_ammessi_non_sono_in_tabella():
    stati = list(Stato)
    ammesse = set(TRANSIZIONI)
    assert (Stato.IN_ANALISI, Stato.CHIUSA) not in ammesse
    assert (Stato.DA_SMISTARE, Stato.IN_LAVORAZIONE) not in ammesse
    assert all(a != d for d, a in ammesse) and all(d in stati and a in stati for d, a in ammesse)


@pytest.mark.parametrize("da,a,chi,atteso", [
    (Stato.IN_LAVORAZIONE, Stato.CHIUSA, "op", 200),
    (Stato.IN_LAVORAZIONE, Stato.CHIUSA, "smi", 200),
    (Stato.DA_VALIDARE, Stato.CHIUSA, "smi", 409),
    (Stato.DA_SMISTARE, Stato.IN_LAVORAZIONE, "smi", 409),
    (Stato.DA_VALIDARE, Stato.IN_LAVORAZIONE, "op", 409),   # solo con la validazione (fase 3)
    (Stato.IN_ANALISI, Stato.DA_SMISTARE, "smi", 409),      # solo il sistema
])
def test_transizioni_generiche(s, accedi, crea_pratica, da, a, chi, atteso):
    p = crea_pratica(da, s["a"] if da != Stato.IN_ANALISI and da != Stato.DA_SMISTARE else None)
    r = accedi(s[chi]).post(f"{P}/pratiche/{p.id}/stato", json={"versione": p.versione, "a_stato": a.value})
    assert r.status_code == atteso, r.text


def test_riapertura_solo_smistatore_con_motivo(s, accedi, crea_pratica):
    p = crea_pratica(Stato.CHIUSA, s["a"])
    assert accedi(s["op"]).post(f"{P}/pratiche/{p.id}/stato",
                                json={"versione": 1, "a_stato": "IN_LAVORAZIONE", "motivo": "x"}).status_code == 403
    c = accedi(s["smi"])
    assert c.post(f"{P}/pratiche/{p.id}/stato", json={"versione": 1, "a_stato": "IN_LAVORAZIONE"}).status_code == 422
    r = c.post(f"{P}/pratiche/{p.id}/stato", json={"versione": 1, "a_stato": "IN_LAVORAZIONE", "motivo": "nuovo elemento"})
    assert r.status_code == 200 and r.json()["stato"] == "IN_LAVORAZIONE"


# --- assegnazione e restituzione ------------------------------------------------------

def test_assegnazione_porta_a_da_validare_e_registra(s, accedi, crea_pratica, db):
    p = crea_pratica(Stato.DA_SMISTARE)
    r = accedi(s["smi"]).post(f"{P}/pratiche/{p.id}/assegnazione",
                              json={"versione": 1, "ufficio_id": str(s["a"].id), "da_proposta_ia": True})
    assert r.status_code == 200
    j = r.json()
    assert j["stato"] == "DA_VALIDARE" and j["ufficio"]["id"] == str(s["a"].id) and j["versione"] == 2
    assert azioni(db, p.id) == ["pratica.assegna"]
    storico = accedi(s["smi"]).get(f"{P}/pratiche/{p.id}/storico").json()
    assert [v["tipo"] for v in storico] == ["assegnazione", "cambio_stato"] or {v["tipo"] for v in storico} == {"assegnazione", "cambio_stato"}


def test_riassegnazione_richiede_motivo_e_ufficio_diverso(s, accedi, crea_pratica, db):
    p = crea_pratica(Stato.DA_VALIDARE, s["a"])
    c = accedi(s["smi"])
    url = f"{P}/pratiche/{p.id}/assegnazione"
    assert c.post(url, json={"versione": 1, "ufficio_id": str(s["b"].id)}).status_code == 422
    assert c.post(url, json={"versione": 1, "ufficio_id": str(s["a"].id), "motivo": "x"}).status_code == 422
    r = c.post(url, json={"versione": 1, "ufficio_id": str(s["b"].id), "motivo": "competenza"})
    assert r.status_code == 200 and r.json()["stato"] == "DA_VALIDARE"
    assert azioni(db, p.id) == ["pratica.riassegna"]


def test_assegnazione_a_ufficio_disattivato_rifiutata(s, accedi, crea_pratica, crea_ufficio):
    spento = crea_ufficio(attivo=False)
    p = crea_pratica(Stato.DA_SMISTARE)
    r = accedi(s["smi"]).post(f"{P}/pratiche/{p.id}/assegnazione", json={"versione": 1, "ufficio_id": str(spento.id)})
    assert r.status_code == 422


def test_assegnazione_stato_sbagliato(s, accedi, crea_pratica):
    for stato in (Stato.IN_ANALISI, Stato.IN_LAVORAZIONE, Stato.CHIUSA):
        p = crea_pratica(stato, s["a"] if stato != Stato.IN_ANALISI else None)
        r = accedi(s["smi"]).post(f"{P}/pratiche/{p.id}/assegnazione",
                                  json={"versione": 1, "ufficio_id": str(s["b"].id), "motivo": "x"})
        assert r.status_code == 409


def test_restituzione_toglie_visibilita_e_richiede_motivo(s, accedi, crea_pratica, db):
    p = crea_pratica(Stato.DA_VALIDARE, s["a"])
    c = accedi(s["op"])
    url = f"{P}/pratiche/{p.id}/restituzione"
    assert c.post(url, json={"versione": 1, "motivo": "   "}).status_code == 422
    r = c.post(url, json={"versione": 1, "motivo": "non è di nostra competenza"})
    assert r.status_code == 200 and r.json()["stato"] == "DA_SMISTARE" and r.json()["ufficio"] is None
    assert c.get(f"{P}/pratiche/{p.id}").status_code == 404
    assert azioni(db, p.id) == ["pratica.restituisci"]


def test_smistatore_non_restituisce(s, accedi, crea_pratica):
    p = crea_pratica(Stato.DA_VALIDARE, s["a"])
    assert accedi(s["smi"]).post(f"{P}/pratiche/{p.id}/restituzione", json={"versione": 1, "motivo": "x"}).status_code == 403


# --- blocco ottimistico ----------------------------------------------------------------------

def test_versione_vecchia_dà_409(s, accedi, crea_pratica):
    p = crea_pratica(Stato.DA_SMISTARE)
    c = accedi(s["smi"])
    assert c.patch(f"{P}/pratiche/{p.id}", json={"versione": 1, "titolo": "Nuovo titolo"}).status_code == 200
    assert c.patch(f"{P}/pratiche/{p.id}", json={"versione": 1, "titolo": "Altro"}).status_code == 409


# --- registro ----------------------------------------------------------------------------------

def test_ogni_scrittura_produce_una_riga_di_registro(s, accedi, crea_pratica, db):
    p = crea_pratica(Stato.DA_SMISTARE)
    c = accedi(s["smi"])
    c.patch(f"{P}/pratiche/{p.id}", json={"versione": 1, "titolo": "Titolo corretto"})
    c.post(f"{P}/pratiche/{p.id}/note", json={"testo": "contenuto riservato della nota"})
    c.post(f"{P}/pratiche/{p.id}/assegnazione", json={"versione": 2, "ufficio_id": str(s["a"].id)})
    assert azioni(db, p.id) == ["pratica.modifica", "nota.crea", "pratica.assegna"]
    righe = db.execute(select(RegistroAzioni).where(RegistroAzioni.pratica_id == p.id)).scalars().all()
    assert all(r.utente_id == s["smi"].id and r.quando and r.id_richiesta for r in righe)
    assert "contenuto riservato" not in str([r.dettagli for r in righe])  # mai testo delle note


def test_registro_visibile_nella_pratica(s, accedi, crea_pratica):
    p = crea_pratica(Stato.DA_SMISTARE)
    c = accedi(s["smi"])
    c.post(f"{P}/pratiche/{p.id}/note", json={"testo": "n"})
    assert [v["azione"] for v in c.get(f"{P}/pratiche/{p.id}/registro").json()] == ["nota.crea"]


def test_registro_di_sola_aggiunta(db, s, accedi, crea_pratica):
    p = crea_pratica(Stato.DA_SMISTARE)
    accedi(s["smi"]).post(f"{P}/pratiche/{p.id}/note", json={"testo": "n"})
    for sql in ("UPDATE registro_azioni SET azione = 'x'", "DELETE FROM registro_azioni", "TRUNCATE registro_azioni"):
        with pytest.raises(DBAPIError):
            db.execute(text(sql))
        db.rollback()


def test_ricerca_testo_con_caratteri_speciali(s, accedi, crea_pratica, db):
    p = crea_pratica(Stato.DA_SMISTARE)
    c = accedi(s["smi"])
    assert c.get(f"{P}/pratiche?testo={p.protocollo}").json()["total"] == 1
    assert c.get(f"{P}/pratiche?testo=%25%25%25").json()["total"] == 0  # '%' è cercato alla lettera
