"""Matrice ruolo × endpoint × (pratica del proprio ufficio / di altro ufficio / non smistata)."""
import uuid

import pytest

from api.enums import Ruolo, Stato

P = "/api/v1"


@pytest.fixture
def scenario(crea_ufficio, crea_utente, crea_pratica):
    a, b = crea_ufficio(), crea_ufficio()
    return dict(
        uff_a=a, uff_b=b,
        smistatore=crea_utente(Ruolo.smistatore),
        op_a=crea_utente(Ruolo.operatore, a),
        op_b=crea_utente(Ruolo.operatore, b),
        admin=crea_utente(Ruolo.amministratore),
        p_a=crea_pratica(Stato.DA_VALIDARE, a),
        p_b=crea_pratica(Stato.DA_VALIDARE, b),
        p_libera=crea_pratica(Stato.DA_SMISTARE),
    )


# endpoint di lettura su una pratica (S, O)
LETTURE = ["", "/note", "/storico", "/registro", "/valutazione", "/temi", "/attivita", "/collegamenti",
           "/percorso", "/documenti"]


@pytest.mark.parametrize("suffisso", LETTURE)
@pytest.mark.parametrize("chi,pratica,atteso", [
    ("smistatore", "p_a", 200), ("smistatore", "p_b", 200), ("smistatore", "p_libera", 200),
    ("op_a", "p_a", 200), ("op_a", "p_b", 404), ("op_a", "p_libera", 404),
    ("op_b", "p_a", 404), ("op_b", "p_b", 200), ("op_b", "p_libera", 404),
    ("admin", "p_a", 403), ("admin", "p_b", 403), ("admin", "p_libera", 403),
])
def test_lettura_pratica(scenario, accedi, chi, pratica, atteso, suffisso):
    c = accedi(scenario[chi])
    assert c.get(f"{P}/pratiche/{scenario[pratica].id}{suffisso}").status_code == atteso


def test_pratica_inesistente_e_non_visibile_sono_indistinguibili(scenario, accedi):
    c = accedi(scenario["op_a"])
    r1 = c.get(f"{P}/pratiche/{scenario['p_b'].id}")
    r2 = c.get(f"{P}/pratiche/{uuid.uuid4()}")
    assert r1.status_code == r2.status_code == 404
    assert r1.json() == r2.json()


def test_elenco_operatore_solo_proprio_ufficio(scenario, accedi):
    ids = {p["id"] for p in accedi(scenario["op_a"]).get(f"{P}/pratiche?per_page=100").json()["items"]}
    assert str(scenario["p_a"].id) in ids
    assert str(scenario["p_b"].id) not in ids and str(scenario["p_libera"].id) not in ids


def test_elenco_smistatore_vede_tutto(scenario, accedi):
    ids = _tutti_gli_id(accedi(scenario["smistatore"]), f"{P}/pratiche")
    assert {str(scenario[k].id) for k in ("p_a", "p_b", "p_libera")} <= ids


def test_amministratore_non_vede_pratiche(scenario, accedi):
    c = accedi(scenario["admin"])
    for url in ("/pratiche", "/inbox", "/smistamento"):
        assert c.get(P + url).status_code == 403


def test_inbox_operatore_solo_da_validare_del_proprio_ufficio(scenario, accedi, crea_pratica):
    in_lav = crea_pratica(Stato.IN_LAVORAZIONE, scenario["uff_a"])
    ids = {p["id"] for p in accedi(scenario["op_a"]).get(f"{P}/inbox?per_page=100").json()["items"]}
    assert str(scenario["p_a"].id) in ids
    assert str(in_lav.id) not in ids and str(scenario["p_b"].id) not in ids


def _tutti_gli_id(client, url):
    """Scorre le pagine: il database di test è condiviso e cresce, la coda è in ordine di arrivo."""
    ids, page = set(), 1
    while True:
        r = client.get(f"{url}{'&' if '?' in url else '?'}per_page=100&page={page}").json()
        ids |= {p["id"] for p in r["items"]}
        if page * 100 >= r["total"]:
            return ids
        page += 1


def test_smistamento_solo_smistatore(scenario, accedi):
    assert accedi(scenario["op_a"]).get(f"{P}/smistamento").status_code == 403
    ids = _tutti_gli_id(accedi(scenario["smistatore"]), f"{P}/smistamento")
    assert str(scenario["p_libera"].id) in ids and str(scenario["p_a"].id) not in ids


def test_scritture_su_pratica_altrui_danno_404(scenario, accedi):
    c = accedi(scenario["op_a"])
    pid, v = scenario["p_b"].id, scenario["p_b"].versione
    assert c.patch(f"{P}/pratiche/{pid}", json={"versione": v, "titolo": "x"}).status_code == 404
    assert c.post(f"{P}/pratiche/{pid}/note", json={"testo": "x"}).status_code == 404
    assert c.post(f"{P}/pratiche/{pid}/restituzione", json={"versione": v, "motivo": "x"}).status_code == 404
    assert c.post(f"{P}/pratiche/{pid}/stato", json={"versione": v, "a_stato": "CHIUSA"}).status_code == 404


def test_operatore_non_assegna(scenario, accedi):
    c = accedi(scenario["op_a"])
    r = c.post(f"{P}/pratiche/{scenario['p_libera'].id}/assegnazione",
               json={"versione": 1, "ufficio_id": str(scenario["uff_a"].id)})
    assert r.status_code == 403


def test_senza_accesso_401(anonimo, scenario):
    assert anonimo.get(f"{P}/pratiche/{scenario['p_a'].id}").status_code == 401
    assert anonimo.get(f"{P}/uffici").status_code == 401


def test_dopo_riassegnazione_ufficio_precedente_perde_visibilita(scenario, accedi):
    s = accedi(scenario["smistatore"])
    p = scenario["p_a"]
    r = s.post(f"{P}/pratiche/{p.id}/assegnazione", json={
        "versione": p.versione, "ufficio_id": str(scenario["uff_b"].id), "motivo": "competenza diversa"})
    assert r.status_code == 200
    assert accedi(scenario["op_a"]).get(f"{P}/pratiche/{p.id}").status_code == 404
    assert accedi(scenario["op_b"]).get(f"{P}/pratiche/{p.id}").status_code == 200


def test_amministratore_gestisce_solo_uffici_e_utenti(scenario, accedi):
    c = accedi(scenario["admin"])
    assert c.get(f"{P}/utenti").status_code == 200
    assert c.get(f"{P}/uffici").status_code == 200
    for ruolo in ("smistatore", "op_a"):
        o = accedi(scenario[ruolo])
        assert o.get(f"{P}/utenti").status_code == 403
        assert o.post(f"{P}/uffici", json={"codice": "X", "nome": "X"}).status_code == 403
        assert o.get(f"{P}/uffici").status_code == 200


# --- il filtro unico, da solo (seconda difesa: vale anche se un endpoint dimenticasse il controllo di ruolo) ---

def test_pratiche_visibili_a_livello_di_funzione(scenario, db):
    from sqlalchemy import select
    from api.models import Pratica
    from api.permessi import pratiche_visibili
    mie = {scenario[k].id for k in ("p_a", "p_b", "p_libera")}

    def visibili(chi):
        return {p.id for p in db.execute(pratiche_visibili(scenario[chi]).where(Pratica.id.in_(mie))).scalars()}

    assert visibili("smistatore") == mie
    assert visibili("op_a") == {scenario["p_a"].id}
    assert visibili("op_b") == {scenario["p_b"].id}
    assert visibili("admin") == set()          # l'amministratore non vede le pratiche, nemmeno senza il controllo di ruolo


def test_carica_pratica_nega_all_amministratore(scenario, db):
    from fastapi import HTTPException
    from api.permessi import carica_pratica
    with pytest.raises(HTTPException) as e:
        carica_pratica(db, scenario["admin"], scenario["p_a"].id)
    assert e.value.status_code == 404
