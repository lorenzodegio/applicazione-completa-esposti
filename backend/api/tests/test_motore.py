"""Prove end-to-end con il finto motore: caricamento → coda → worker → risultato → API."""
import hashlib
from pathlib import Path

import pytest
from sqlalchemy import select

from api.archivio import get_archivio
from api.config import get_settings
from api.enums import Ruolo, Stato, StatoLavoro
from api.models import Documento, LavoroMotore, Pratica, RegistroAzioni, RisultatoMotore
from api.worker import esegui_coda
from motore.client import motore_finto_in_processo

P = "/api/v1"
PDF = "application/pdf"


@pytest.fixture
def motore():
    return motore_finto_in_processo()


@pytest.fixture
def worker(motore):
    """Svuota la coda con il finto motore; prima toglie gli avanzi di altri test."""
    def _esegui() -> dict[str, int]:
        return esegui_coda(client=motore, archivio=get_archivio(), dormi=lambda s: None)
    _esegui()
    return _esegui


@pytest.fixture
def s(crea_ufficio, crea_utente):
    a = crea_ufficio()
    return dict(a=a, smi=crea_utente(Ruolo.smistatore), op=crea_utente(Ruolo.operatore, a),
                op2=crea_utente(Ruolo.operatore, crea_ufficio()), admin=crea_utente(Ruolo.amministratore))


def carica(client, *nomi, **campi):
    files = [("files", (n, f"contenuto sintetico di {n}".encode(), PDF)) for n in nomi]
    r = client.post(f"{P}/pratiche", files=files, data=campi)
    assert r.status_code == 201, r.text
    return r.json()


def azioni(db, pratica_id):
    return [r.azione for r in db.execute(select(RegistroAzioni).where(RegistroAzioni.pratica_id == pratica_id)
                                         .order_by(RegistroAzioni.id)).scalars()]


# --- caricamento --------------------------------------------------------------------------

def test_caricamento_crea_pratica_in_analisi_con_lavoro_in_coda(s, accedi, db):
    r = carica(accedi(s["smi"]), "esposto_cani.pdf", protocollo="0004512/2025")
    pid = r["pratica"]["id"]
    assert r["pratica"]["stato"] == "IN_ANALISI" and r["pratica"]["ufficio"] is None
    assert r["pratica"]["numero"].startswith("ESP-") and r["documenti"][0]["principale"]
    assert r["documenti"][0]["analisi"]["stato"] == "in_corso"
    assert azioni(db, pid) == ["pratica.crea", "documento.carica", "motore.accoda"]


def test_solo_lo_smistatore_crea_pratiche(s, accedi):
    for chi in ("op", "admin"):
        r = accedi(s[chi]).post(f"{P}/pratiche", files=[("files", ("a.pdf", b"x", PDF))])
        assert r.status_code == 403


def test_caricamento_senza_file_o_file_vuoto(s, accedi):
    c = accedi(s["smi"])
    assert c.post(f"{P}/pratiche", data={"titolo": "x"}).status_code == 422
    assert c.post(f"{P}/pratiche", files=[("files", ("vuoto.pdf", b"", PDF))]).status_code == 422


def test_file_troppo_grande_rifiutato_e_non_resta_in_archivio(s, accedi, monkeypatch, db):
    monkeypatch.setattr(get_settings(), "max_mb_per_file", 0)
    prima = {p for p in get_archivio().radice.rglob("*") if p.is_file()}
    r = accedi(s["smi"]).post(f"{P}/pratiche", files=[("files", ("grande.pdf", b"x" * 10, PDF))])
    assert r.status_code == 413
    assert {p for p in get_archivio().radice.rglob("*") if p.is_file()} == prima   # nessun avanzo in archivio


def test_il_nome_del_file_non_entra_nel_percorso_in_archivio(s, accedi, db):
    r = carica(accedi(s["smi"]), "../../mario_rossi_esposto.pdf")
    doc = db.get(Documento, r["documenti"][0]["id"])
    assert "mario" not in doc.id_archivio and doc.nome_file == "mario_rossi_esposto.pdf"


# --- worker: percorso felice ----------------------------------------------------------------------

def test_esposto_pulito_dal_caricamento_alla_proposta(s, accedi, worker, db, dir_temp, motore):
    smi = accedi(s["smi"])
    r = carica(smi, "esposto_cani.pdf")
    pid, did = r["pratica"]["id"], r["documenti"][0]["id"]
    assert worker().get("completato", 0) >= 1

    d = smi.get(f"{P}/pratiche/{pid}").json()
    assert d["stato"] == "DA_SMISTARE" and d["ufficio"] is None          # niente assegnazioni automatiche
    assert d["stato_analisi"]["stato"] == "completata" and d["avvisi"] == []
    assert d["tipo"] == "esposto" and d["comune"] == "Borgoverde" and d["protocollo"] == "0004512/2025"
    a = d["analisi"]
    assert a["proposta"]["esito"] == "Accolto" and a["proposta"]["urgenza"] == "Normale"
    assert a["scheda"]["comune"]["frase"] and a["scheda"]["ambito"][0]["pagina"] == 1
    assert a["temi_proposti"][0]["valore"] == "Cani" and a["valori_non_riconosciuti"] == []

    assert azioni(db, pid) == ["pratica.crea", "documento.carica", "motore.accoda", "temi.proponi",
                               "motore.completato", "pratica.analisi_conclusa"]
    storico = smi.get(f"{P}/pratiche/{pid}/storico").json()
    assert [v["dettagli"]["a"] for v in storico if v["tipo"] == "cambio_stato"] == ["IN_ANALISI", "DA_SMISTARE"]
    # niente resta in giro: temporanei cancellati, il motore ha ricevuto la conferma
    assert not list(dir_temp.iterdir()) and motore._c.app.state.finto.lavori == {}


def test_testo_per_pagina_sta_in_archivio_non_nel_database(s, accedi, worker, db):
    smi = accedi(s["smi"])
    r = carica(smi, "esposto_cani.pdf")
    did = r["documenti"][0]["id"]
    worker()
    doc = db.get(Documento, did)
    assert doc.id_archivio_testo.endswith(".testo.json") and doc.sha256_testo and doc.tipo_documento == "esposto"
    assert get_archivio().impronta(doc.id_archivio_testo) == doc.sha256_testo
    testo = smi.get(f"{P}/documenti/{did}/testo").json()
    assert "cinque cani" in testo["pagine"][0]["testo"]
    ris = db.execute(select(RisultatoMotore).where(RisultatoMotore.documento_id == doc.id)).scalar_one()
    nel_db = str(ris.scheda) + str(ris.proposta) + str(ris.temi_proposti) + str(ris.acquisizione)
    assert testo["pagine"][0]["testo"] not in nel_db                       # il testo delle pagine non è nel database
    assert "documento.testo" in azioni(db, r["pratica"]["id"])


def test_manoscritto_lettura_incerta_genera_avviso(s, accedi, worker):
    smi = accedi(s["smi"])
    pid = carica(smi, "foglio_manoscritto.pdf")["pratica"]["id"]
    worker()
    d = smi.get(f"{P}/pratiche/{pid}").json()
    assert d["analisi"]["lettura_incerta"] and d["analisi"]["pagine_incerte"] == [2]
    assert d["analisi"]["acquisizione"] == {"1": "testo_nativo", "2": "ocr_manoscritto"}
    assert [a["codice"] for a in d["avvisi"]] == ["lettura_incerta"] and d["avvisi"][0]["pagine"] == [2]
    assert d["analisi"]["proposta"]["da_verificare_sull_originale"]


def test_riscontro_riconosciuto(s, accedi, worker):
    smi = accedi(s["smi"])
    pid = carica(smi, "riscontro_ats.pdf")["pratica"]["id"]
    worker()
    d = smi.get(f"{P}/pratiche/{pid}").json()
    assert d["tipo"] == "riscontro_ats" and d["protocollo"] == "0003177/2025"


def test_la_precompilazione_non_sovrascrive_quello_che_c_e_gia(s, accedi, worker):
    smi = accedi(s["smi"])
    pid = carica(smi, "esposto_cani.pdf", protocollo="9999999/2025", comune="Altro Comune")["pratica"]["id"]
    worker()
    d = smi.get(f"{P}/pratiche/{pid}").json()
    assert d["protocollo"] == "9999999/2025" and d["comune"] == "Altro Comune"
    assert d["analisi"]["protocollo_letto"] == "0004512/2025"            # il letto resta nel risultato


# --- worker: errori e tentativi --------------------------------------------------------------------

def test_errore_non_ritentabile_la_pratica_va_comunque_allo_smistamento(s, accedi, worker, db):
    smi = accedi(s["smi"])
    r = carica(smi, "lettera.pages")
    worker()
    lavoro = db.execute(select(LavoroMotore).where(LavoroMotore.pratica_id == r["pratica"]["id"])).scalar_one()
    assert lavoro.stato == StatoLavoro.errore and lavoro.codice_errore == "formato_non_supportato" and lavoro.tentativi == 1
    d = smi.get(f"{P}/pratiche/{r['pratica']['id']}").json()
    assert d["stato"] == "DA_SMISTARE" and d["analisi"] is None
    assert d["stato_analisi"]["stato"] == "non_disponibile" and d["avvisi"][0]["codice"] == "analisi_non_disponibile"


def test_errore_ritentabile_tre_tentativi_poi_analisi_non_disponibile(s, accedi, worker, db):
    smi = accedi(s["smi"])
    r = carica(smi, "esposto_scaduto.pdf")
    worker()
    lavoro = db.execute(select(LavoroMotore).where(LavoroMotore.pratica_id == r["pratica"]["id"])).scalar_one()
    assert lavoro.tentativi == 3 and lavoro.stato == StatoLavoro.errore and lavoro.codice_errore == "tempo_scaduto"
    assert azioni(db, r["pratica"]["id"]).count("motore.ritenta") == 2
    assert smi.get(f"{P}/pratiche/{r['pratica']['id']}").json()["stato"] == "DA_SMISTARE"


def test_errore_instabile_riesce_al_secondo_tentativo(s, accedi, worker, db):
    smi = accedi(s["smi"])
    r = carica(smi, "esposto_instabile.pdf")
    worker()
    lavoro = db.execute(select(LavoroMotore).where(LavoroMotore.pratica_id == r["pratica"]["id"])).scalar_one()
    assert lavoro.stato == StatoLavoro.completato and lavoro.tentativi == 2
    assert smi.get(f"{P}/pratiche/{r['pratica']['id']}").json()["analisi"] is not None


def test_motore_occupato_riprova_senza_consumare_tentativi(s, accedi, worker, db):
    r = carica(accedi(s["smi"]), "esposto_occupato.pdf")
    worker()
    lavoro = db.execute(select(LavoroMotore).where(LavoroMotore.pratica_id == r["pratica"]["id"])).scalar_one()
    assert lavoro.stato == StatoLavoro.completato and lavoro.tentativi == 1


def test_risultato_fuori_contratto_errore_che_nomina_solo_i_campi(s, accedi, worker, db):
    r = carica(accedi(s["smi"]), "esposto_invalido.pdf")
    worker()
    lavoro = db.execute(select(LavoroMotore).where(LavoroMotore.pratica_id == r["pratica"]["id"])).scalar_one()
    assert lavoro.stato == StatoLavoro.errore and lavoro.codice_errore == "risultato_non_valido" and lavoro.tentativi == 1
    riga = db.execute(select(RegistroAzioni).where(RegistroAzioni.pratica_id == r["pratica"]["id"],
                                                   RegistroAzioni.azione == "motore.errore")).scalar_one()
    assert any("frase" in c for c in riga.dettagli["campi"]) and "xxx" not in str(riga.dettagli)


def test_documento_manomesso_in_archivio_non_viene_inviato(s, accedi, worker, db, motore):
    r = carica(accedi(s["smi"]), "esposto_cani.pdf")
    doc = db.get(Documento, r["documenti"][0]["id"])
    (get_archivio().radice / doc.id_archivio).write_bytes(b"altro contenuto")
    worker()
    lavoro = db.execute(select(LavoroMotore).where(LavoroMotore.pratica_id == doc.pratica_id)).scalar_one()
    assert lavoro.codice_errore == "archivio_non_disponibile" and lavoro.tentativi == 1
    assert motore._c.app.state.finto.lavori == {}                        # nulla è arrivato al motore


def test_lavoro_rimasto_a_meta_riprende(s, accedi, worker, db):
    r = carica(accedi(s["smi"]), "esposto_cani.pdf")
    lavoro = db.execute(select(LavoroMotore).where(LavoroMotore.pratica_id == r["pratica"]["id"])).scalar_one()
    lavoro.stato, lavoro.tentativi = StatoLavoro.in_corso, 1            # il worker si è fermato qui
    db.commit()
    worker()
    db.refresh(lavoro)
    assert lavoro.stato == StatoLavoro.completato and "motore.riprendi" in azioni(db, lavoro.pratica_id)


# --- più documenti, rilancio -----------------------------------------------------------------------

def test_pratica_con_piu_documenti_esce_da_analisi_solo_alla_fine(s, accedi, worker, db, motore):
    smi = accedi(s["smi"])
    r = carica(smi, "esposto_cani.pdf", "riscontro_ats.pdf")
    pid = r["pratica"]["id"]
    worker()
    assert smi.get(f"{P}/pratiche/{pid}").json()["stato"] == "DA_SMISTARE"
    docs = smi.get(f"{P}/pratiche/{pid}/documenti").json()
    assert [d["analisi"]["stato"] for d in docs] == ["completata", "completata"]
    assert docs[0]["principale"] and not docs[1]["principale"]
    assert smi.get(f"{P}/pratiche/{pid}").json()["tipo"] == "esposto"   # conta il documento principale


def test_rilancio_nuovo_lavoro_ultimo_risultato_per_primo(s, accedi, worker):
    smi = accedi(s["smi"])
    r = carica(smi, "esposto_cani.pdf")
    did = r["documenti"][0]["id"]
    worker()
    assert len(smi.get(f"{P}/documenti/{did}/analisi").json()) == 1
    nuovo = smi.post(f"{P}/documenti/{did}/analisi")
    assert nuovo.status_code == 202 and nuovo.json()["stato"] == "in_coda"
    assert smi.post(f"{P}/documenti/{did}/analisi").status_code == 409    # già in corso
    assert smi.get(f"{P}/lavori/{nuovo.json()['id']}").json()["stato"] == "in_coda"
    worker()
    ris = smi.get(f"{P}/documenti/{did}/analisi").json()
    assert len(ris) == 2 and ris[0]["ricevuto_il"] >= ris[1]["ricevuto_il"]
    assert ris[0]["lavoro_id"] == nuovo.json()["id"]


def test_rilancio_fallito_mantiene_il_risultato_precedente_con_avviso(s, accedi, worker, db):
    smi = accedi(s["smi"])
    r = carica(smi, "esposto_instabile.pdf")
    did, pid = r["documenti"][0]["id"], r["pratica"]["id"]
    worker()
    doc = db.get(Documento, did)
    doc.nome_file = "esposto_scaduto.pdf"                                 # il prossimo giro fallirà sempre
    db.commit()
    smi.post(f"{P}/documenti/{did}/analisi")
    worker()
    d = smi.get(f"{P}/pratiche/{pid}").json()
    assert d["analisi"] is not None and d["stato_analisi"]["stato"] == "non_disponibile"
    assert d["avvisi"][0]["codice"] == "analisi_non_disponibile" and "precedente" in d["avvisi"][0]["testo"]


def test_valori_fuori_vocabolario_si_segnalano_senza_bloccare(s, accedi, worker, db):
    smi = accedi(s["smi"])
    r = carica(smi, "esposto_cani.pdf")
    worker()
    ris = db.execute(select(RisultatoMotore).where(RisultatoMotore.pratica_id == r["pratica"]["id"])).scalar_one()
    ris.scheda = {**ris.scheda, "ambito": [{"valore": "Ambito Inventato", "frase": "x", "pagina": 1}]}
    ris.temi_proposti = [{"valore": "Tema Nuovo", "motivo": "m", "frase": "f", "pagina": 1}]
    db.commit()
    d = smi.get(f"{P}/pratiche/{r['pratica']['id']}").json()
    assert {"campo": "scheda.ambito", "valore": "Ambito Inventato"} in d["analisi"]["valori_non_riconosciuti"]
    assert {"campo": "temi", "valore": "Tema Nuovo"} in d["analisi"]["valori_non_riconosciuti"]
    assert "valori_non_riconosciuti" in [a["codice"] for a in d["avvisi"]]


# --- permessi sui documenti ------------------------------------------------------------------------

def test_documenti_e_analisi_seguono_il_perimetro_della_pratica(s, accedi, worker, db):
    smi = accedi(s["smi"])
    r = carica(smi, "esposto_cani.pdf")
    pid, did = r["pratica"]["id"], r["documenti"][0]["id"]
    worker()
    versione = smi.get(f"{P}/pratiche/{pid}").json()["versione"]
    assert smi.post(f"{P}/pratiche/{pid}/assegnazione",
                    json={"versione": versione, "ufficio_id": str(s["a"].id)}).status_code == 200
    urls = [f"{P}/documenti/{did}/analisi", f"{P}/documenti/{did}/testo", f"{P}/documenti/{did}/contenuto",
            f"{P}/pratiche/{pid}/documenti"]
    for u in urls:
        assert accedi(s["op"]).get(u).status_code == 200, u
        assert accedi(s["op2"]).get(u).status_code == 404, u            # altro ufficio: non esiste
        assert accedi(s["admin"]).get(u).status_code == 403, u
    assert accedi(s["op2"]).post(f"{P}/documenti/{did}/analisi").status_code == 404
    assert accedi(s["op2"]).post(f"{P}/pratiche/{pid}/documenti", files=[("files", ("a.pdf", b"x", PDF))]).status_code == 404


def test_contenuto_restituisce_i_byte_originali_e_registra_l_apertura(s, accedi, db):
    smi = accedi(s["smi"])
    r = carica(smi, "esposto_cani.pdf")
    did, pid = r["documenti"][0]["id"], r["pratica"]["id"]
    resp = smi.get(f"{P}/documenti/{did}/contenuto")
    atteso = b"contenuto sintetico di esposto_cani.pdf"
    assert resp.status_code == 200 and resp.content == atteso
    assert resp.headers["content-type"] == PDF and resp.headers["x-content-type-options"] == "nosniff"
    assert "documento.apri" in azioni(db, pid)
    assert hashlib.sha256(resp.content).hexdigest() == r["documenti"][0]["sha256"]


def test_aggiunta_documento_a_pratica_esistente_accoda_il_motore(s, accedi, worker, db):
    smi = accedi(s["smi"])
    r = carica(smi, "esposto_cani.pdf")
    pid = r["pratica"]["id"]
    worker()
    nuovo = smi.post(f"{P}/pratiche/{pid}/documenti", files=[("files", ("riscontro_ats.pdf", b"yy", PDF))])
    assert nuovo.status_code == 201 and nuovo.json()[0]["analisi"]["stato"] == "in_corso"
    worker()
    docs = smi.get(f"{P}/pratiche/{pid}/documenti").json()
    assert [d["analisi"]["stato"] for d in docs] == ["completata", "completata"]
    assert smi.get(f"{P}/pratiche/{pid}").json()["stato"] == "DA_SMISTARE"   # lo stato non si muove da solo
