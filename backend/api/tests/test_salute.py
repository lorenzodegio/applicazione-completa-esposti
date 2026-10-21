"""GET /api/v1/salute: database, archivio, coda, motore (senza dati sensibili)."""
import httpx
from fastapi.testclient import TestClient

from api import salute as modulo_salute
from api.config import get_settings
from documenti import ErroreArchivio
from motore.finto.app import crea_app

P = "/api/v1/salute"


def test_tutto_bene_con_il_finto_nello_stesso_processo(anonimo, monkeypatch):
    monkeypatch.setattr(get_settings(), "motore_url", "")
    r = anonimo.get(P)
    assert r.status_code == 200
    c = r.json()
    assert (c["stato"], c["database"], c["archivio"]) == ("ok", "ok", "ok")
    assert c["coda"]["stato"] == "ok" and c["coda"]["in_coda"] >= 0 and c["coda"]["in_corso"] >= 0
    assert c["motore"]["stato"] == "in_processo" and c["versione_contratto_applicazione"] == "1.2"


def test_motore_http_raggiungibile_riporta_versioni(anonimo, monkeypatch):
    monkeypatch.setattr(get_settings(), "motore_url", "http://motore-finto:8080")
    monkeypatch.setattr(modulo_salute.httpx, "Client",
                        lambda **kw: TestClient(crea_app(), base_url=kw["base_url"]))
    c = anonimo.get(P).json()
    assert c["stato"] == "ok"
    assert c["motore"] == {"stato": "ok", "stato_dichiarato": "pronto", "versione_motore": "finto-1.0.0",
                           "versione_contratto": "1.2", "contratto_compatibile": True, "occupato": False}


def test_motore_irraggiungibile_degradato_ma_200_e_senza_url(anonimo, monkeypatch):
    monkeypatch.setattr(get_settings(), "motore_url", "http://127.0.0.1:9")    # nessuno in ascolto
    r = anonimo.get(P)
    assert r.status_code == 200 and r.json()["stato"] == "degradato"
    assert r.json()["motore"]["stato"] == "irraggiungibile"
    assert "127.0.0.1" not in r.text and "http" not in r.text


def _motore_che_dice(monkeypatch, **salute):
    corpo = {"stato": "pronto", "versione_motore": "sintetico-9", "versione_contratto": "1.2", "occupato": False, **salute}

    class MotoreSintetico:
        def __init__(self, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def request(self, metodo, percorso, **kw):
            return httpx.Response(200, json=corpo)
    monkeypatch.setattr(get_settings(), "motore_url", "http://motore:8080")
    monkeypatch.setattr(modulo_salute.httpx, "Client", MotoreSintetico)


def test_contratto_diverso_degradato(anonimo, monkeypatch):
    _motore_che_dice(monkeypatch, versione_contratto="2.0")
    r = anonimo.get(P)
    assert r.status_code == 200 and r.json()["stato"] == "degradato"
    assert r.json()["motore"]["stato"] == "contratto_diverso" and r.json()["motore"]["contratto_compatibile"] is False


def test_altra_versione_minore_del_contratto_va_bene(anonimo, monkeypatch):
    _motore_che_dice(monkeypatch, versione_contratto="1.1")
    c = anonimo.get(P).json()
    assert c["stato"] == "ok" and c["motore"]["stato"] == "ok" and c["motore"]["contratto_compatibile"] is True


def test_motore_non_pronto_degradato(anonimo, monkeypatch):
    _motore_che_dice(monkeypatch, stato="non_pronto")       # es. modello assente o digest diversi
    r = anonimo.get(P)
    assert r.status_code == 200 and r.json()["stato"] == "degradato"
    assert r.json()["motore"]["stato"] == "non_pronto" and r.json()["motore"]["stato_dichiarato"] == "non_pronto"


def test_il_timeout_dell_applicazione_supera_quello_del_motore():
    from api.config import Settings
    assert Settings().motore_timeout_secondi > 1800          # tempo_max_s del motore vero: lo dichiara lui


def test_archivio_non_disponibile_503(anonimo, monkeypatch):
    class Rotto:
        def verifica(self):
            raise ErroreArchivio("percorso interno /segreto")
    monkeypatch.setattr(get_settings(), "motore_url", "")
    monkeypatch.setattr(modulo_salute, "get_archivio", lambda: Rotto())
    r = anonimo.get(P)
    assert r.status_code == 503 and r.json()["stato"] == "errore" and r.json()["archivio"] == "errore"
    assert "segreto" not in r.text
