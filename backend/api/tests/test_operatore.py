"""Lavoro dell'operatore: valutazione, validazione (Inbox), temi, attività, disaccordo."""
import pytest
from sqlalchemy import select, text

from api.archivio import get_archivio
from api.enums import Ruolo, Stato
from api.models import Pratica, PraticaTema, RegistroAzioni, Valutazione
from api.worker import esegui_coda
from motore.client import motore_finto_in_processo

P = "/api/v1"
PDF = "application/pdf"


@pytest.fixture
def worker():
    motore = motore_finto_in_processo()
    def _esegui():
        return esegui_coda(client=motore, archivio=get_archivio(), dormi=lambda s: None)
    _esegui()
    return _esegui


@pytest.fixture
def s(crea_ufficio, crea_utente):
    a, b = crea_ufficio(), crea_ufficio()
    return dict(a=a, b=b, smi=crea_utente(Ruolo.smistatore), op=crea_utente(Ruolo.operatore, a),
                op_b=crea_utente(Ruolo.operatore, b), admin=crea_utente(Ruolo.amministratore))


@pytest.fixture
def da_validare(s, accedi, worker):
    """Pratica analizzata dal finto motore (esposto_cani) e assegnata all'ufficio A."""
    def _crea(nome="esposto_cani.pdf") -> str:
        smi = accedi(s["smi"])
        pid = smi.post(f"{P}/pratiche", files=[("files", (nome, f"contenuto di {nome}".encode(), PDF))]).json()["pratica"]["id"]
        worker()
        v = smi.get(f"{P}/pratiche/{pid}").json()["versione"]
        assert smi.post(f"{P}/pratiche/{pid}/assegnazione", json={"versione": v, "ufficio_id": str(s["a"].id)}).status_code == 200
        return pid
    return _crea


def azioni(db, pid):
    return [r.azione for r in db.execute(select(RegistroAzioni).where(RegistroAzioni.pratica_id == pid)
                                         .order_by(RegistroAzioni.id)).scalars()]


def modulo(**k):
    base = {"esito": "Accolto", "urgenza": "Normale", "azione": ["Sopralluogo congiunto"], "ambito": ["Medicina Veterinaria"],
            "problematica": ["Condizione di inidonea detenzione"], "elementi": ["Ferite/sofferenza animale"], "comune": "Borgoverde"}
    base.update(k)
    return base


# --- proposta → precompilazione → valutazione ---------------------------------------------------------

def test_temi_proposti_dal_motore_e_precompilazione(s, accedi, da_validare):
    pid = da_validare()
    op = accedi(s["op"])
    temi = op.get(f"{P}/pratiche/{pid}/temi").json()
    assert [(t["codice"], t["origine"], t["stato"]) for t in temi] == [("cani", "ia", "proposto")]
    assert temi[0]["motivo"] and temi[0]["frase"] and temi[0]["pagina"] == 1
    v = op.get(f"{P}/pratiche/{pid}/valutazione").json()
    assert v["valutazione"] is None and v["disaccordo"] == []
    pre = v["precompilazione"]
    assert pre["esito"] == "Accolto" and pre["ambito"] == ["Medicina Veterinaria"] and pre["valori_scartati"] == []


def test_le_righe_di_elenco_portano_la_proposta_dell_ia(s, accedi, da_validare):
    pid = da_validare()
    riga = next(r for r in accedi(s["op"]).get(f"{P}/inbox?per_page=100").json()["items"] if r["id"] == pid)
    assert riga["proposta"] == {"esito": "Accolto", "urgenza": "Normale"} and riga["valutazione"] is None


def test_la_precompilazione_non_viene_salvata(s, accedi, da_validare, db):
    pid = da_validare()
    accedi(s["op"]).get(f"{P}/pratiche/{pid}/valutazione")
    assert db.execute(select(Valutazione).where(Valutazione.pratica_id == pid)).scalar_one_or_none() is None


def test_bozza_e_poi_valutazione_compilata(s, accedi, da_validare, db):
    pid = da_validare()
    op = accedi(s["op"])
    r = op.put(f"{P}/pratiche/{pid}/valutazione", json={"comune": "Borgoverde", "compilata": False})
    assert r.status_code == 200 and r.json()["compilata"] is False and r.json()["data_compilazione"] is None
    # una bozza non cancella la precompilazione
    assert op.get(f"{P}/pratiche/{pid}/valutazione").json()["precompilazione"] is not None
    r = op.put(f"{P}/pratiche/{pid}/valutazione", json=modulo())
    assert r.status_code == 200 and r.json()["compilata"] and r.json()["origine"] == "applicazione"
    assert r.json()["autore_id"] == str(s["op"].id) and r.json()["da_risultato_id"]
    assert op.get(f"{P}/pratiche/{pid}/valutazione").json()["precompilazione"] is None
    assert azioni(db, pid).count("valutazione.salva") == 2


def test_valori_fuori_vocabolario_e_confermare_senza_esito(s, accedi, da_validare):
    pid = da_validare()
    op = accedi(s["op"])
    r = op.put(f"{P}/pratiche/{pid}/valutazione", json=modulo(ambito=["Inventato"]))
    assert r.status_code == 422 and r.json()["detail"]["campi"] == [{"campo": "ambito", "valore": "Inventato"}]
    assert op.put(f"{P}/pratiche/{pid}/valutazione", json=modulo(urgenza=None)).status_code == 422


def test_registro_della_valutazione_ha_prima_dopo_ma_non_i_testi_liberi(s, accedi, da_validare, db):
    pid = da_validare()
    op = accedi(s["op"])
    op.put(f"{P}/pratiche/{pid}/valutazione", json=modulo(note="dato riservato del segnalante"))
    op.put(f"{P}/pratiche/{pid}/valutazione", json=modulo(urgenza="Alta", note="altro dato riservato"))
    righe = db.execute(select(RegistroAzioni).where(RegistroAzioni.pratica_id == pid,
                       RegistroAzioni.azione == "valutazione.salva").order_by(RegistroAzioni.id)).scalars().all()
    assert righe[1].dettagli["prima"]["urgenza"] == "Normale" and righe[1].dettagli["dopo"]["urgenza"] == "Alta"
    assert "riservato" not in str([r.dettagli for r in righe])


def test_valutazione_ats_compilata_si_sovrascrive_solo_con_conferma(s, accedi, da_validare, db):
    pid = da_validare()
    db.add(Valutazione(pratica_id=pid, origine="import_ats", autore_nome="Operatore ATS (sintetico)", compilata=True,
                       esito="Archiviato", urgenza="Bassa", azione=[]))
    db.commit()
    op = accedi(s["op"])
    r = op.put(f"{P}/pratiche/{pid}/valutazione", json=modulo())
    assert r.status_code == 409
    r = op.put(f"{P}/pratiche/{pid}/valutazione", json=modulo(conferma_sovrascrittura=True))
    assert r.status_code == 200 and r.json()["origine"] == "applicazione" and r.json()["autore_nome"] is None


# --- disaccordo IA–operatore -----------------------------------------------------------------------------

def test_disaccordo_calcolato_e_filtrabile(s, accedi, da_validare):
    d = da_validare()
    op = accedi(s["op"])
    assert op.get(f"{P}/pratiche?disaccordo=true&per_page=100").json()["total"] == 0
    op.put(f"{P}/pratiche/{d}/valutazione", json=modulo())            # come l'IA: nessun disaccordo
    assert op.get(f"{P}/pratiche/{d}/valutazione").json()["disaccordo"] == []
    op.put(f"{P}/pratiche/{d}/valutazione", json=modulo(urgenza="Alta", azione=["Sopralluogo", "Contatto segnalante"]))
    campi = {c["campo"]: c for c in op.get(f"{P}/pratiche/{d}/valutazione").json()["disaccordo"]}
    assert campi["urgenza"] == {"campo": "urgenza", "ia": "Normale", "operatore": "Alta"}
    assert campi["azione"]["ia"] == ["Sopralluogo congiunto"] and "esito" not in campi
    ids = [p["id"] for p in op.get(f"{P}/pratiche?disaccordo=true&per_page=100").json()["items"]]
    assert ids == [d]
    riga = op.get(f"{P}/pratiche?disaccordo=true").json()["items"][0]
    assert riga["valutazione"]["urgenza"] == "Alta" and {c["campo"] for c in riga["disaccordo"]} == {"urgenza", "azione"}
    assert op.get(f"{P}/pratiche/{d}").json()["disaccordo"]
    assert op.get(f"{P}/pratiche?disaccordo=false&per_page=100").json()["total"] == 0


def test_stesse_azioni_in_ordine_diverso_non_sono_disaccordo(s, accedi, da_validare, db):
    from api.models import RisultatoMotore
    pid = da_validare()
    r = db.execute(select(RisultatoMotore).where(RisultatoMotore.pratica_id == pid)).scalar_one()
    r.proposta = {**r.proposta, "azione": ["Sopralluogo", "Contatto segnalante"]}
    db.commit()
    op = accedi(s["op"])
    op.put(f"{P}/pratiche/{pid}/valutazione", json=modulo(azione=["Contatto segnalante", "Sopralluogo"]))
    assert op.get(f"{P}/pratiche/{pid}").json()["disaccordo"] == []
    op.put(f"{P}/pratiche/{pid}/valutazione", json=modulo(azione=["Sopralluogo"]))
    assert [c["campo"] for c in op.get(f"{P}/pratiche/{pid}").json()["disaccordo"]] == ["azione"]


def test_una_bozza_non_conta_come_disaccordo(s, accedi, da_validare):
    pid = da_validare()
    op = accedi(s["op"])
    op.put(f"{P}/pratiche/{pid}/valutazione", json={"esito": "Archiviato", "urgenza": "Alta", "compilata": False})
    assert op.get(f"{P}/pratiche/{pid}").json()["disaccordo"] == []


# --- validazione (Inbox) ------------------------------------------------------------------------------------

def test_validazione_porta_in_lavorazione_e_conferma_i_temi(s, accedi, da_validare, db):
    pid = da_validare()
    op = accedi(s["op"])
    v = op.get(f"{P}/pratiche/{pid}").json()["versione"]
    r = op.post(f"{P}/pratiche/{pid}/validazione", json={
        "versione": v, "valutazione": modulo(), "temi": [{"codice": "cani", "stato": "confermato"},
                                                         {"codice": "avvelenamenti", "stato": "confermato"}]})
    assert r.status_code == 200 and r.json()["stato"] == "IN_LAVORAZIONE" and r.json()["versione"] == v + 1
    temi = {t["codice"]: t for t in op.get(f"{P}/pratiche/{pid}/temi").json()}
    assert temi["cani"]["stato"] == "confermato" and temi["cani"]["origine"] == "ia" and temi["cani"]["deciso_da"] == str(s["op"].id)
    assert temi["avvelenamenti"]["origine"] == "operatore"
    assert azioni(db, pid)[-3:] == ["valutazione.conferma", "temi.decidi", "pratica.valida"]
    assert op.get(f"{P}/pratiche/{pid}").json()["temi"][0]["codice"] == "cani"


def test_validazione_richiede_di_decidere_ogni_tema_proposto(s, accedi, da_validare):
    pid = da_validare()
    op = accedi(s["op"])
    v = op.get(f"{P}/pratiche/{pid}").json()["versione"]
    r = op.post(f"{P}/pratiche/{pid}/validazione", json={"versione": v, "valutazione": modulo(), "temi": []})
    assert r.status_code == 422 and r.json()["detail"]["temi"] == ["Cani"]
    assert op.get(f"{P}/pratiche/{pid}").json()["stato"] == "DA_VALIDARE"      # niente a metà


def test_validazione_atomica_se_la_valutazione_e_invalida(s, accedi, da_validare, db):
    pid = da_validare()
    op = accedi(s["op"])
    v = op.get(f"{P}/pratiche/{pid}").json()["versione"]
    r = op.post(f"{P}/pratiche/{pid}/validazione", json={"versione": v, "valutazione": modulo(esito=None),
                                                         "temi": [{"codice": "cani", "stato": "confermato"}]})
    assert r.status_code == 422
    assert db.execute(select(Valutazione).where(Valutazione.pratica_id == pid)).scalar_one_or_none() is None
    assert [t.stato.value for t in db.execute(select(PraticaTema).where(PraticaTema.pratica_id == pid)).scalars()] == ["proposto"]


def test_validazione_regole_di_stato_e_versione(s, accedi, da_validare):
    pid = da_validare()
    op = accedi(s["op"])
    corpo = lambda v: {"versione": v, "valutazione": modulo(), "temi": [{"codice": "cani", "stato": "scartato"}]}
    assert op.post(f"{P}/pratiche/{pid}/validazione", json=corpo(1)).status_code == 409      # versione vecchia
    v = op.get(f"{P}/pratiche/{pid}").json()["versione"]
    assert op.post(f"{P}/pratiche/{pid}/validazione", json=corpo(v)).status_code == 200
    assert op.post(f"{P}/pratiche/{pid}/validazione", json=corpo(v + 1)).status_code == 409  # già validata


def test_validazione_di_pratica_altrui_404_e_admin_403(s, accedi, da_validare):
    pid = da_validare()
    corpo = {"versione": 1, "valutazione": modulo(), "temi": []}
    assert accedi(s["op_b"]).post(f"{P}/pratiche/{pid}/validazione", json=corpo).status_code == 404
    assert accedi(s["admin"]).post(f"{P}/pratiche/{pid}/validazione", json=corpo).status_code == 403
    assert accedi(s["op_b"]).put(f"{P}/pratiche/{pid}/valutazione", json=modulo()).status_code == 404
    assert accedi(s["op_b"]).put(f"{P}/pratiche/{pid}/temi", json={"temi": []}).status_code == 404


def test_validazione_di_una_pratica_ats_gia_valutata_chiede_conferma(s, accedi, da_validare, db):
    pid = da_validare()
    db.add(Valutazione(pratica_id=pid, origine="import_ats", autore_nome="ATS (sintetico)", compilata=True,
                       esito="Accolto", urgenza="Bassa", azione=[]))
    db.commit()
    op = accedi(s["op"])
    corpo = {"versione": 2, "valutazione": modulo(), "temi": [{"codice": "cani", "stato": "confermato"}]}
    corpo["versione"] = op.get(f"{P}/pratiche/{pid}").json()["versione"]
    assert op.post(f"{P}/pratiche/{pid}/validazione", json=corpo).status_code == 409
    corpo["valutazione"]["conferma_sovrascrittura"] = True
    assert op.post(f"{P}/pratiche/{pid}/validazione", json=corpo).status_code == 200


# --- temi dopo la validazione --------------------------------------------------------------------------------

def test_temi_si_aggiungono_e_si_scartano_dopo(s, accedi, da_validare):
    pid = da_validare()
    op = accedi(s["op"])
    v = op.get(f"{P}/pratiche/{pid}").json()["versione"]
    op.post(f"{P}/pratiche/{pid}/validazione", json={"versione": v, "valutazione": modulo(),
                                                      "temi": [{"codice": "cani", "stato": "confermato"}]})
    r = op.put(f"{P}/pratiche/{pid}/temi", json={"temi": [{"codice": "cani", "stato": "scartato"},
                                                         {"codice": "gatti_colonie_feline", "stato": "confermato"}]})
    assert {(t["codice"], t["stato"]) for t in r.json()} == {("cani", "scartato"), ("gatti_colonie_feline", "confermato")}
    assert op.put(f"{P}/pratiche/{pid}/temi", json={"temi": [{"codice": "animali_da_reddito", "stato": "scartato"}]}).status_code == 422
    assert op.put(f"{P}/pratiche/{pid}/temi", json={"temi": [{"codice": "boh", "stato": "confermato"}]}).status_code == 422
    assert op.put(f"{P}/pratiche/{pid}/temi", json={"temi": [{"codice": "cani", "stato": "proposto"}]}).status_code == 422


def test_rianalisi_non_tocca_le_decisioni_gia_prese(s, accedi, da_validare, worker):
    pid = da_validare()
    op = accedi(s["op"])
    v = op.get(f"{P}/pratiche/{pid}").json()["versione"]
    op.post(f"{P}/pratiche/{pid}/validazione", json={"versione": v, "valutazione": modulo(),
                                                      "temi": [{"codice": "cani", "stato": "scartato"}]})
    did = accedi(s["smi"]).get(f"{P}/pratiche/{pid}/documenti").json()[0]["id"]
    assert op.post(f"{P}/documenti/{did}/analisi").status_code == 202
    worker()
    assert [(t["codice"], t["stato"]) for t in op.get(f"{P}/pratiche/{pid}/temi").json()] == [("cani", "scartato")]


# --- attività -------------------------------------------------------------------------------------------------

@pytest.fixture
def in_lavorazione(s, accedi, da_validare):
    pid = da_validare()
    op = accedi(s["op"])
    v = op.get(f"{P}/pratiche/{pid}").json()["versione"]
    op.post(f"{P}/pratiche/{pid}/validazione", json={"versione": v, "valutazione": modulo(),
                                                      "temi": [{"codice": "cani", "stato": "confermato"}]})
    return pid


def test_attivita_ciclo_di_vita(s, accedi, in_lavorazione, db):
    pid, op = in_lavorazione, accedi(s["op"])
    r = op.post(f"{P}/pratiche/{pid}/attivita", json={"tipo": "Sopralluogo", "data_prevista": "2026-11-03", "descrizione": "x"})
    assert r.status_code == 201 and r.json()["stato"] == "prevista"
    aid = r.json()["id"]
    assert op.patch(f"{P}/attivita/{aid}", json={"stato": "in_corso"}).json()["stato"] == "in_corso"
    c = op.patch(f"{P}/attivita/{aid}", json={"stato": "conclusa"}).json()
    assert c["stato"] == "conclusa" and c["data_conclusione"]
    assert op.patch(f"{P}/attivita/{aid}", json={"stato": "in_corso"}).status_code == 409   # conclusa: chiusa
    assert op.get(f"{P}/pratiche/{pid}/attivita").json()[0]["tipo"] == "Sopralluogo"
    assert {"attivita.crea", "attivita.modifica"} <= set(azioni(db, pid))


def test_attivita_regole(s, accedi, in_lavorazione, da_validare):
    pid, op = in_lavorazione, accedi(s["op"])
    assert op.post(f"{P}/pratiche/{pid}/attivita", json={"tipo": "Inventata"}).status_code == 422
    a = op.post(f"{P}/pratiche/{pid}/attivita", json={"tipo": "Sopralluogo"}).json()["id"]
    assert accedi(s["op_b"]).patch(f"{P}/attivita/{a}", json={"stato": "in_corso"}).status_code == 404
    assert accedi(s["admin"]).patch(f"{P}/attivita/{a}", json={"stato": "in_corso"}).status_code == 403
    assert accedi(s["op_b"]).get(f"{P}/pratiche/{pid}/attivita").status_code == 404
    altra = da_validare()                                        # ancora DA_VALIDARE: niente attività
    assert op.post(f"{P}/pratiche/{altra}/attivita", json={"tipo": "Sopralluogo"}).status_code == 409
    assert accedi(s["op"]).patch(f"{P}/attivita/{a}", json={"stato": "annullata"}).status_code == 200


def test_attivita_non_sul_registro_con_la_descrizione(s, accedi, in_lavorazione, db):
    op = accedi(s["op"])
    op.post(f"{P}/pratiche/{in_lavorazione}/attivita", json={"tipo": "Sopralluogo", "descrizione": "nome del segnalante"})
    righe = db.execute(select(RegistroAzioni).where(RegistroAzioni.pratica_id == in_lavorazione)).scalars().all()
    assert "segnalante" not in str([r.dettagli for r in righe])


# --- migrazione: la vista e il registro restano coerenti -----------------------------------------------------------

def test_registro_ancora_immutabile_dopo_la_0004(db):
    from sqlalchemy.exc import DBAPIError
    with pytest.raises(DBAPIError):
        db.execute(text("DELETE FROM registro_azioni"))
    db.rollback()
