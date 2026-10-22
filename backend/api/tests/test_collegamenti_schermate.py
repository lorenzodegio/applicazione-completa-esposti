"""Collegamenti, percorso, fascicoli, Home e filtri di Gestione pratiche."""
import pytest
from sqlalchemy import select

from api.archivio import get_archivio
from api.enums import Ruolo, Stato
from api.models import Collegamento, Pratica, RegistroAzioni, TipoCollegamento
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
def tipo(db):
    return lambda codice: db.execute(select(TipoCollegamento).where(TipoCollegamento.codice == codice)).scalar_one()


def modulo(**k):
    base = {"esito": "Accolto", "urgenza": "Normale", "azione": ["Sopralluogo congiunto"], "ambito": ["Medicina Veterinaria"]}
    base.update(k)
    return base


def azioni(db, pid):
    return [r.azione for r in db.execute(select(RegistroAzioni).where(RegistroAzioni.pratica_id == pid)
                                         .order_by(RegistroAzioni.id)).scalars()]


# --- collegamenti ------------------------------------------------------------------------------------------

def test_collegamento_automatico_per_stesso_protocollo(s, accedi, crea_pratica, db):
    p1, p2 = crea_pratica(Stato.DA_VALIDARE, s["a"]), crea_pratica(Stato.DA_VALIDARE, s["a"])
    p2.protocollo = p1.protocollo
    db.commit()
    r = accedi(s["op"]).get(f"{P}/pratiche/{p1.id}/collegamenti").json()
    assert len(r) == 1 and r[0]["automatico"] and r[0]["id"] is None and r[0]["tipo"]["codice"] == "STESSO_PROTOCOLLO"
    assert r[0]["pratica"]["id"] == str(p2.id) and r[0]["pratica"]["titolo"]


@pytest.mark.parametrize("prot1,data1,prot2,data2,collegate", [
    ("{n}/2025", None, "{n}/2025", None, True),
    ("{n} / 2025", None, "{n}/2025", None, True),            # spazi e maiuscole non contano
    ("{n}", None, "{n}", None, False),                       # solo cifre, nessun anno: mai uniti
    ("{n}", "2024-03-01", "{n}", "2025-03-01", False),       # stesso numero, anni diversi
    ("{n}", "2025-01-10", "{n}", "2025-11-30", True),        # anno dalla data del protocollo
    ("{n}/2025", None, "{n}", "2025-06-01", True),
    ("{n}/2024", None, "{n}", "2025-06-01", False),
    ("{n}/2024", None, "{n}/2025", None, False),
])
def test_stesso_protocollo_richiede_numero_e_anno(s, accedi, crea_pratica, db, prot1, data1, prot2, data2, collegate):
    import datetime as dt
    import uuid as _uuid
    n = str(_uuid.uuid4().int)[:9]
    p1, p2 = crea_pratica(Stato.DA_VALIDARE, s["a"]), crea_pratica(Stato.DA_VALIDARE, s["a"])
    p1.protocollo, p2.protocollo = prot1.format(n=n), prot2.format(n=n)
    p1.data_protocollo = dt.date.fromisoformat(data1) if data1 else None
    p2.data_protocollo = dt.date.fromisoformat(data2) if data2 else None
    db.commit()
    op = accedi(s["op"])
    automatici = [c for c in op.get(f"{P}/pratiche/{p1.id}/collegamenti").json() if c["automatico"]]
    assert bool(automatici) is collegate
    riga = next(r for r in op.get(f"{P}/pratiche?testo={n}&per_page=100").json()["items"] if r["id"] == str(p1.id))
    assert riga["n_collegate"] == (1 if collegate else 0)


def test_pratica_collegata_di_altro_ufficio_solo_numero_ufficio_stato(s, accedi, crea_pratica, db):
    mia, altrui = crea_pratica(Stato.DA_VALIDARE, s["a"]), crea_pratica(Stato.IN_LAVORAZIONE, s["b"])
    altrui.protocollo = mia.protocollo
    db.commit()
    voce = accedi(s["op"]).get(f"{P}/pratiche/{mia.id}/collegamenti").json()[0]["pratica"]
    assert voce["id"] is None and voce["numero"] == altrui.numero and voce["stato"] == "IN_LAVORAZIONE"
    assert voce["ufficio"]["id"] == str(s["b"].id)
    assert voce["titolo"] is None and voce["protocollo"] is None and voce["comune"] is None and voce["tipo"] is None
    # lo smistatore la vede per intero
    assert accedi(s["smi"]).get(f"{P}/pratiche/{mia.id}/collegamenti").json()[0]["pratica"]["id"] == str(altrui.id)


def test_collegamento_manuale_con_verso_ed_etichette(s, accedi, crea_pratica, tipo, db):
    a, b = crea_pratica(Stato.IN_LAVORAZIONE, s["a"]), crea_pratica(Stato.IN_LAVORAZIONE, s["a"])
    op = accedi(s["op"])
    r = op.post(f"{P}/pratiche/{a.id}/collegamenti", json={"pratica_id": str(b.id), "tipo_id": str(tipo("INTEGRAZIONE").id),
                                                           "nota": "integra la prima"})
    assert r.status_code == 201 and r.json()["etichetta"] == "Integra" and not r.json()["automatico"]
    da_b = op.get(f"{P}/pratiche/{b.id}/collegamenti").json()
    assert da_b[0]["etichetta"] == "Integrata da" and da_b[0]["pratica"]["id"] == str(a.id)
    assert "collegamento.crea" in azioni(db, a.id) and "collegamento.crea" in azioni(db, b.id)
    # n_collegate nella riga di elenco
    righe = {x["id"]: x for x in op.get(f"{P}/pratiche?per_page=100").json()["items"]}
    assert righe[str(a.id)]["n_collegate"] == 1 and righe[str(b.id)]["n_collegate"] == 1


def test_collegamento_simmetrico_non_si_duplica_nei_due_versi(s, accedi, crea_pratica, tipo):
    a, b = crea_pratica(Stato.IN_LAVORAZIONE, s["a"]), crea_pratica(Stato.IN_LAVORAZIONE, s["a"])
    op, t = accedi(s["op"]), str(tipo("CORRELATA").id)
    assert op.post(f"{P}/pratiche/{a.id}/collegamenti", json={"pratica_id": str(b.id), "tipo_id": t}).status_code == 201
    assert op.post(f"{P}/pratiche/{b.id}/collegamenti", json={"pratica_id": str(a.id), "tipo_id": t}).status_code == 409
    assert op.post(f"{P}/pratiche/{a.id}/collegamenti", json={"pratica_id": str(b.id), "tipo_id": t}).status_code == 409


def test_collegamento_regole(s, accedi, crea_pratica, tipo):
    mia, altrui = crea_pratica(Stato.IN_LAVORAZIONE, s["a"]), crea_pratica(Stato.IN_LAVORAZIONE, s["b"])
    op, t = accedi(s["op"]), str(tipo("CORRELATA").id)
    assert op.post(f"{P}/pratiche/{mia.id}/collegamenti", json={"pratica_id": str(altrui.id), "tipo_id": t}).status_code == 404
    assert op.post(f"{P}/pratiche/{mia.id}/collegamenti", json={"pratica_id": str(mia.id), "tipo_id": t}).status_code == 422
    auto = str(tipo("STESSO_PROTOCOLLO").id)
    ok = crea_pratica(Stato.IN_LAVORAZIONE, s["a"])
    assert op.post(f"{P}/pratiche/{mia.id}/collegamenti", json={"pratica_id": str(ok.id), "tipo_id": auto}).status_code == 422
    assert accedi(s["admin"]).get(f"{P}/pratiche/{mia.id}/collegamenti").status_code == 403
    assert accedi(s["smi"]).post(f"{P}/pratiche/{mia.id}/collegamenti",
                                 json={"pratica_id": str(altrui.id), "tipo_id": t}).status_code == 201


def test_rimozione_logica_con_registro(s, accedi, crea_pratica, tipo, db):
    a, b = crea_pratica(Stato.IN_LAVORAZIONE, s["a"]), crea_pratica(Stato.IN_LAVORAZIONE, s["a"])
    op = accedi(s["op"])
    cid = op.post(f"{P}/pratiche/{a.id}/collegamenti", json={"pratica_id": str(b.id), "tipo_id": str(tipo("CORRELATA").id)}).json()["id"]
    assert accedi(s["op_b"]).delete(f"{P}/collegamenti/{cid}").status_code == 404     # non vede nessuno dei due lati
    assert op.delete(f"{P}/collegamenti/{cid}").status_code == 204
    assert op.get(f"{P}/pratiche/{a.id}/collegamenti").json() == []
    c = db.get(Collegamento, cid); db.refresh(c)
    assert c.rimosso_il is not None and c.rimosso_da == s["op"].id                    # c'è ancora, rimosso
    assert "collegamento.rimuovi" in azioni(db, a.id)
    assert op.delete(f"{P}/collegamenti/{cid}").status_code == 404
    # si può ricreare dopo la rimozione
    assert op.post(f"{P}/pratiche/{a.id}/collegamenti", json={"pratica_id": str(b.id), "tipo_id": str(tipo("CORRELATA").id)}).status_code == 201


def test_ricerca_rapida_solo_pratiche_visibili(s, accedi, crea_pratica, db):
    mia, altrui = crea_pratica(Stato.IN_LAVORAZIONE, s["a"]), crea_pratica(Stato.IN_LAVORAZIONE, s["b"])
    mia.titolo, altrui.titolo = "Zebrette in giardino xk7", "Zebrette altrove xk7"
    db.commit()
    op = accedi(s["op"])
    r = op.get(f"{P}/pratiche/ricerca-rapida?q=xk7").json()
    assert [x["id"] for x in r] == [str(mia.id)]
    assert {x["id"] for x in accedi(s["smi"]).get(f"{P}/pratiche/ricerca-rapida?q=xk7").json()} == {str(mia.id), str(altrui.id)}
    assert op.get(f"{P}/pratiche/ricerca-rapida?q=xk7&escludi={mia.id}").json() == []
    assert op.get(f"{P}/pratiche/ricerca-rapida?q=x").status_code == 422             # troppo corta
    assert op.get(f"{P}/pratiche/ricerca-rapida?q=%25%25").json() == []               # '%' alla lettera


# --- percorso ----------------------------------------------------------------------------------------------------

def carica(smi, nome):
    return smi.post(f"{P}/pratiche", files=[("files", (nome, f"contenuto di {nome}".encode(), PDF))]).json()["pratica"]["id"]


def test_percorso_completo_di_un_esposto(s, accedi, worker, crea_pratica, db):
    smi, op = accedi(s["smi"]), accedi(s["op"])
    pid = carica(smi, "esposto_cani.pdf")
    assert [(x["passo"], x["stato"]) for x in smi.get(f"{P}/pratiche/{pid}/percorso").json()] == [
        ("esposto", "concluso"), ("proposta_ia", "in_corso")]
    worker()
    passi = smi.get(f"{P}/pratiche/{pid}/percorso").json()
    assert [(x["passo"], x["stato"]) for x in passi] == [
        ("esposto", "concluso"), ("proposta_ia", "concluso"), ("smistamento", "atteso")]
    assert passi[0]["documento_id"] and passi[0]["pagina"] == 1 and "Accolto" in passi[1]["testo"]
    v = smi.get(f"{P}/pratiche/{pid}").json()["versione"]
    smi.post(f"{P}/pratiche/{pid}/assegnazione", json={"versione": v, "ufficio_id": str(s["a"].id)})
    assert [(x["passo"], x["stato"]) for x in op.get(f"{P}/pratiche/{pid}/percorso").json()] == [
        ("esposto", "concluso"), ("proposta_ia", "concluso"), ("smistamento", "concluso"),
        ("validazione", "atteso"), ("riscontro", "atteso")]
    v = op.get(f"{P}/pratiche/{pid}").json()["versione"]
    op.post(f"{P}/pratiche/{pid}/validazione", json={"versione": v, "valutazione": modulo(),
                                                      "temi": [{"codice": "cani", "stato": "confermato"}]})
    a = op.post(f"{P}/pratiche/{pid}/attivita", json={"tipo": "Sopralluogo"}).json()["id"]
    passi = op.get(f"{P}/pratiche/{pid}/percorso").json()
    assert [(x["passo"], x["stato"]) for x in passi][3:] == [("validazione", "concluso"), ("azione", "atteso"), ("riscontro", "atteso")]
    assert "Valutata da" in passi[3]["testo"]
    op.patch(f"{P}/attivita/{a}", json={"stato": "conclusa"})
    # arriva il riscontro (stesso protocollo): il passo si chiude e rimanda alla pratica collegata
    mio = db.get(Pratica, pid); db.refresh(mio)
    r = crea_pratica(Stato.DA_SMISTARE); r.tipo, r.protocollo = "riscontro_ats", mio.protocollo
    db.commit()
    ultimo = op.get(f"{P}/pratiche/{pid}/percorso").json()[-1]
    assert ultimo["passo"] == "riscontro" and ultimo["stato"] == "concluso"
    assert ultimo["pratica_collegata"]["id"] is None and ultimo["pratica_collegata"]["numero"] == r.numero   # non è del suo ufficio


def test_percorso_con_riassegnazione_e_analisi_non_disponibile(s, accedi, worker):
    smi = accedi(s["smi"])
    pid = carica(smi, "lettera.pages")
    worker()
    passi = smi.get(f"{P}/pratiche/{pid}/percorso").json()
    assert passi[1]["titolo"] == "Analisi non disponibile"
    for uff, motivo in ((s["a"], None), (s["b"], "competenza diversa")):
        v = smi.get(f"{P}/pratiche/{pid}").json()["versione"]
        smi.post(f"{P}/pratiche/{pid}/assegnazione", json={"versione": v, "ufficio_id": str(uff.id), "motivo": motivo})
    titoli = [x["titolo"] for x in smi.get(f"{P}/pratiche/{pid}/percorso").json() if x["passo"] == "smistamento"]
    assert titoli == [f"Assegnata a {s['a'].nome}", f"Riassegnata a {s['b'].nome}"]


def test_percorso_rispetta_il_perimetro(s, accedi, crea_pratica):
    p = crea_pratica(Stato.IN_LAVORAZIONE, s["a"])
    assert accedi(s["op_b"]).get(f"{P}/pratiche/{p.id}/percorso").status_code == 404
    assert accedi(s["admin"]).get(f"{P}/pratiche/{p.id}/percorso").status_code == 403


# --- fascicoli ---------------------------------------------------------------------------------------------------------

def valida(op, pid, temi):
    v = op.get(f"{P}/pratiche/{pid}").json()["versione"]
    r = op.post(f"{P}/pratiche/{pid}/validazione", json={"versione": v, "valutazione": modulo(), "temi": temi})
    assert r.status_code == 200, r.text


def test_fascicolo_conta_solo_temi_confermati_e_pratiche_visibili(s, accedi, worker, crea_utente):
    smi = accedi(s["smi"])
    tutti = []
    for nome in ("esposto_cani.pdf", "esposto_cani_due.pdf", "esposto_cani_tre.pdf"):
        pid = carica(smi, nome)
        tutti.append(pid)
    worker()
    for pid in tutti:
        v = smi.get(f"{P}/pratiche/{pid}").json()["versione"]
        uff = s["a"] if pid != tutti[2] else s["b"]
        smi.post(f"{P}/pratiche/{pid}/assegnazione", json={"versione": v, "ufficio_id": str(uff.id)})
    op, op_b = accedi(s["op"]), accedi(s["op_b"])
    valida(op, tutti[0], [{"codice": "cani", "stato": "confermato"}])
    valida(op, tutti[1], [{"codice": "cani", "stato": "scartato"}])          # scartato: non è nel fascicolo
    valida(op_b, tutti[2], [{"codice": "cani", "stato": "confermato"}])

    def n(client):
        return {f["codice"]: f["pratiche"] for f in client.get(f"{P}/fascicoli").json()}["cani"]
    assert n(smi) >= 2 and n(op) >= 1
    ids_op = [p["id"] for p in op.get(f"{P}/fascicoli/cani/pratiche?per_page=100").json()["items"]]
    assert tutti[0] in ids_op and tutti[1] not in ids_op and tutti[2] not in ids_op      # solo il suo ufficio
    ids_smi = [p["id"] for p in smi.get(f"{P}/fascicoli/cani/pratiche?per_page=100").json()["items"]]
    assert tutti[0] in ids_smi and tutti[2] in ids_smi and tutti[1] not in ids_smi
    riga = next(p for p in op.get(f"{P}/fascicoli/cani/pratiche?per_page=100").json()["items"] if p["id"] == tutti[0])
    assert riga["temi"] == ["Cani"]
    assert op.get(f"{P}/fascicoli/inesistente/pratiche").status_code == 404
    assert accedi(s["admin"]).get(f"{P}/fascicoli").status_code == 403


def test_fascicolo_in_ordine_di_tempo(s, accedi, crea_pratica, db):
    smi = accedi(s["smi"])
    p_nuova, p_vecchia = crea_pratica(Stato.IN_LAVORAZIONE, s["a"]), crea_pratica(Stato.IN_LAVORAZIONE, s["a"])
    import datetime as dt
    p_nuova.data_protocollo, p_vecchia.data_protocollo = dt.date(2025, 6, 1), dt.date(2024, 1, 1)
    from api.models import PraticaTema, Tema
    t = db.execute(select(Tema).where(Tema.codice == "avvelenamenti")).scalar_one()
    for p in (p_nuova, p_vecchia):
        db.add(PraticaTema(pratica_id=p.id, tema_id=t.id, origine="operatore", stato="confermato"))
    db.commit()
    ids = [x["id"] for x in smi.get(f"{P}/fascicoli/avvelenamenti/pratiche").json()["items"]]
    assert ids.index(str(p_vecchia.id)) < ids.index(str(p_nuova.id))


# --- filtri di Gestione pratiche -----------------------------------------------------------------------------------

def test_filtri_tema_tipo_ats_lettura_incerta_date(s, accedi, worker, db):
    from api.models import Valutazione
    smi = accedi(s["smi"])
    pulito, incerto = carica(smi, "esposto_cani.pdf"), carica(smi, "foglio_manoscritto.pdf")
    worker()
    op = accedi(s["op"])
    ids = lambda q: {p["id"] for p in smi.get(f"{P}/pratiche?per_page=100&{q}").json()["items"]}
    assert incerto in ids("lettura_incerta=true") and pulito not in ids("lettura_incerta=true")
    assert pulito in ids("lettura_incerta=false")
    riga = next(p for p in smi.get(f"{P}/pratiche?per_page=100&lettura_incerta=true").json()["items"] if p["id"] == incerto)
    assert riga["lettura_incerta"] is True
    assert pulito in ids("tipo=esposto") and pulito not in ids("tipo=riscontro_ats")
    db.add(Valutazione(pratica_id=pulito, origine="import_ats", autore_nome="ATS (sintetico)", compilata=True, esito="Accolto", urgenza="Bassa", azione=[]))
    db.commit()
    assert pulito in ids("con_valutazione_ats=true") and incerto not in ids("con_valutazione_ats=true")
    assert incerto in ids("con_valutazione_ats=false")
    assert pulito in ids("dal=2000-01-01&al=2999-12-31") and pulito not in ids("al=2000-01-01")
    assert smi.get(f"{P}/pratiche?stato=INESISTENTE").status_code == 422


# --- Home --------------------------------------------------------------------------------------------------------------------

def test_home_operatore_conta_solo_il_suo_ufficio(s, accedi, crea_pratica, db):
    n = lambda c, k: c.get(f"{P}/home").json()["contatori"][k]
    op, op_b, smi = accedi(s["op"]), accedi(s["op_b"]), accedi(s["smi"])
    prima = {k: n(op, k) for k in ("da_validare", "in_lavorazione")}
    prima_b, prima_s = n(op_b, "da_validare"), n(smi, "da_validare")
    crea_pratica(Stato.DA_VALIDARE, s["a"]); crea_pratica(Stato.DA_VALIDARE, s["a"]); crea_pratica(Stato.IN_LAVORAZIONE, s["a"])
    crea_pratica(Stato.DA_VALIDARE, s["b"])
    assert n(op, "da_validare") == prima["da_validare"] + 2 and n(op, "in_lavorazione") == prima["in_lavorazione"] + 1
    assert n(op_b, "da_validare") == prima_b + 1 and n(smi, "da_validare") == prima_s + 3
    assert "da_smistare" in smi.get(f"{P}/home").json()["contatori"] and "da_smistare" not in op.get(f"{P}/home").json()["contatori"]
    assert accedi(s["admin"]).get(f"{P}/home").status_code == 403


def test_home_senza_riscontro_e_lettura_incerta(s, accedi, crea_pratica, db):
    op = accedi(s["op"])
    n = lambda k: op.get(f"{P}/home").json()["contatori"][k]
    base = n("senza_riscontro")
    e = crea_pratica(Stato.IN_LAVORAZIONE, s["a"])
    assert n("senza_riscontro") == base + 1
    r = crea_pratica(Stato.DA_SMISTARE); r.tipo, r.protocollo = "riscontro_ats", e.protocollo
    db.commit()
    assert n("senza_riscontro") == base                                   # arrivato il riscontro (stesso protocollo)
    e2 = crea_pratica(Stato.IN_LAVORAZIONE, s["a"])
    assert n("senza_riscontro") == base + 1
    r2 = crea_pratica(Stato.DA_SMISTARE); r2.tipo = "riscontro_ats"
    db.commit()
    from api.models import TipoCollegamento
    t = db.execute(select(TipoCollegamento).where(TipoCollegamento.codice == "RISCONTRO")).scalar_one()
    smi = accedi(s["smi"])
    smi.post(f"{P}/pratiche/{e2.id}/collegamenti", json={"pratica_id": str(r2.id), "tipo_id": str(t.id)})
    assert n("senza_riscontro") == base                                   # collegamento manuale di tipo RISCONTRO


def test_home_liste(s, accedi, worker):
    smi = accedi(s["smi"])
    pid = carica(smi, "foglio_manoscritto.pdf")
    worker()
    v = smi.get(f"{P}/pratiche/{pid}").json()["versione"]
    smi.post(f"{P}/pratiche/{pid}/assegnazione", json={"versione": v, "ufficio_id": str(s["a"].id)})
    op = accedi(s["op"])
    h = op.get(f"{P}/home").json()
    assert [x["id"] for x in h["ultimi_arrivi"]] == [pid] and h["ultimi_arrivi"][0]["lettura_incerta"]
    assert h["contatori"]["lettura_incerta"] >= 1 and len(h["fascicoli_piu_attivi"]) <= 5
    assert h["disaccordo"]["totale"] == 0
    op.put(f"{P}/pratiche/{pid}/valutazione", json=modulo(urgenza="Immediata"))
    h = op.get(f"{P}/home").json()
    assert h["disaccordo"]["totale"] == 1 and h["disaccordo"]["pratiche"][0]["id"] == pid
    assert h["disaccordo"]["pratiche"][0]["disaccordo"][0]["campo"] == "urgenza"


# --- configurazione ----------------------------------------------------------------------------------------------------------------

def test_vocabolari_temi_tipi_per_tutti_i_ruoli(s, accedi, anonimo):
    for chi in ("smi", "op", "admin"):
        c = accedi(s[chi])
        v = c.get(f"{P}/vocabolari").json()
        assert "Medicina Veterinaria" in [x["codice"] for x in v["ambito"]] and "Veterinario" not in [x["codice"] for x in v["ambito"]]
        assert {"esito", "urgenza", "azione", "problematica", "elementi", "tipo_documento"} <= set(v)
        assert "cani" in [t["codice"] for t in c.get(f"{P}/temi").json()]
        assert "STESSO_PROTOCOLLO" in [t["codice"] for t in c.get(f"{P}/tipi-collegamento").json()]
    assert anonimo.get(f"{P}/vocabolari").status_code == 401
