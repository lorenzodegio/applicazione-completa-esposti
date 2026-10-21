import pytest
from sqlalchemy import select

from api.enums import Ruolo
from api.models import RegistroAzioni, Utente
from conftest import PASSWORD

P = "/api/v1"


def test_login_ok_menu_per_ruolo(crea_utente, crea_ufficio, anonimo):
    for ruolo, voci in ((Ruolo.smistatore, 5), (Ruolo.operatore, 4), (Ruolo.amministratore, 2)):
        u = crea_utente(ruolo, crea_ufficio() if ruolo == Ruolo.operatore else None)
        r = anonimo.post(f"{P}/auth/login", json={"username": u.username, "password": PASSWORD})
        assert r.status_code == 200 and len(r.json()["menu"]) == voci
        assert "password" not in r.text
    assert "Smistamento" not in r.json()["menu"] and r.json()["menu"] == ["Uffici", "Utenti"]


def test_cookie_sicuro(crea_utente, anonimo):
    u = crea_utente(Ruolo.smistatore)
    r = anonimo.post(f"{P}/auth/login", json={"username": u.username, "password": PASSWORD})
    c = r.headers["set-cookie"].lower()
    assert "httponly" in c and "secure" in c and "samesite=strict" in c


def test_login_errato_registrato_senza_dire_se_esiste(crea_utente, anonimo, db):
    u = crea_utente(Ruolo.smistatore)
    r1 = anonimo.post(f"{P}/auth/login", json={"username": u.username, "password": "sbagliata"})
    r2 = anonimo.post(f"{P}/auth/login", json={"username": "inesistente_xyz", "password": "sbagliata"})
    assert r1.status_code == r2.status_code == 401 and r1.json() == r2.json()
    n = db.execute(select(RegistroAzioni).where(RegistroAzioni.azione == "accesso.fallito",
                   RegistroAzioni.dettagli["username"].as_string() == u.username)).scalars().all()
    assert len(n) == 1 and "sbagliata" not in str(n[0].dettagli)


def test_limite_tentativi(crea_utente, anonimo):
    u = crea_utente(Ruolo.smistatore)
    for _ in range(5):
        assert anonimo.post(f"{P}/auth/login", json={"username": u.username, "password": "no"}).status_code == 401
    # anche con la password giusta, finché dura la finestra
    assert anonimo.post(f"{P}/auth/login", json={"username": u.username, "password": PASSWORD}).status_code == 429


def test_utente_disattivato_non_entra(crea_utente, anonimo):
    u = crea_utente(Ruolo.smistatore, attivo=False)
    assert anonimo.post(f"{P}/auth/login", json={"username": u.username, "password": PASSWORD}).status_code == 401


def test_logout_revoca_la_sessione(crea_utente, accedi):
    c = accedi(crea_utente(Ruolo.smistatore))
    assert c.get(f"{P}/auth/me").status_code == 200
    vecchio = c.cookies.get("esposti_sessione")
    assert c.post(f"{P}/auth/logout").status_code == 204
    c.cookies.set("esposti_sessione", vecchio)
    assert c.get(f"{P}/auth/me").status_code == 401


def test_admin_crea_utente_e_registra_senza_password(crea_utente, crea_ufficio, accedi, db):
    admin, uff = crea_utente(Ruolo.amministratore), crea_ufficio()
    c = accedi(admin)
    r = c.post(f"{P}/utenti", json={"username": "nuovo.op.sint", "nome_visualizzato": "Nuovo", "ruolo": "operatore",
                                    "ufficio_id": str(uff.id), "password": "una-password-lunga-1"})
    assert r.status_code == 201 and "password" not in r.text
    riga = db.execute(select(RegistroAzioni).where(RegistroAzioni.azione == "utente.crea",
                      RegistroAzioni.oggetto_id == r.json()["id"])).scalar_one()
    assert riga.utente_id == admin.id and "password" not in str(riga.dettagli)


@pytest.mark.parametrize("ruolo,con_ufficio,atteso", [
    ("operatore", False, 422), ("smistatore", True, 422), ("amministratore", True, 422),
])
def test_ruolo_e_ufficio_coerenti(crea_utente, crea_ufficio, accedi, ruolo, con_ufficio, atteso):
    c = accedi(crea_utente(Ruolo.amministratore))
    body = {"username": f"x_{ruolo}_{con_ufficio}", "nome_visualizzato": "X", "ruolo": ruolo,
            "password": "una-password-lunga-1"}
    if con_ufficio:
        body["ufficio_id"] = str(crea_ufficio().id)
    assert c.post(f"{P}/utenti", json=body).status_code == atteso


def test_admin_non_si_disattiva_e_disattivare_revoca_sessioni(crea_utente, crea_ufficio, accedi):
    admin = crea_utente(Ruolo.amministratore)
    c = accedi(admin)
    assert c.patch(f"{P}/utenti/{admin.id}", json={"attivo": False}).status_code == 422
    op = crea_utente(Ruolo.operatore, crea_ufficio())
    co = accedi(op)
    assert c.patch(f"{P}/utenti/{op.id}", json={"attivo": False}).status_code == 200
    assert co.get(f"{P}/auth/me").status_code == 401


def test_uffici_si_disattivano_non_si_cancellano(crea_utente, accedi):
    c = accedi(crea_utente(Ruolo.amministratore))
    u = c.post(f"{P}/uffici", json={"codice": "ZZ-T1", "nome": "Ufficio test"}).json()
    assert c.post(f"{P}/uffici", json={"codice": "ZZ-T1", "nome": "doppio"}).status_code == 409
    assert c.patch(f"{P}/uffici/{u['id']}", json={"attivo": False}).json()["attivo"] is False
    assert c.delete(f"{P}/uffici/{u['id']}").status_code == 405
