"""Test su PostgreSQL vero.

Con ESPOSTI_TEST_DATABASE_URL (es. il servizio `db` di Docker) si usa quello;
altrimenti si avvia un PostgreSQL temporaneo con `pgserver` (extra `dev`).
Il database di test è creato con le migrazioni, come in produzione.
Ogni test crea dati con nomi unici: nessuna pulizia (il registro è immutabile).
"""
import os
import shutil
import tempfile
import uuid
from pathlib import Path

import pytest

_server = None
_tmp = None
url = os.environ.get("ESPOSTI_TEST_DATABASE_URL")
if not url:
    import pgserver
    _tmp = tempfile.mkdtemp()
    _server = pgserver.get_server(_tmp)
    url = _server.get_uri().replace("postgresql://", "postgresql+psycopg://")
os.environ["ESPOSTI_DATABASE_URL"] = url
os.environ["ESPOSTI_COOKIE_SECURE"] = "true"
_arch = tempfile.mkdtemp(prefix="esposti-test-archivio-")
_temp = tempfile.mkdtemp(prefix="esposti-test-temp-")
os.environ["ESPOSTI_ARCHIVIO_RADICE"] = _arch
os.environ["ESPOSTI_DIR_TEMPORANEA"] = _temp

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api.db import get_sessionmaker  # noqa: E402
from api.enums import Canale, Ruolo, Stato  # noqa: E402
from api.main import app  # noqa: E402
from api.models import Pratica, Ufficio, Utente  # noqa: E402
from api.security import hash_password  # noqa: E402

PASSWORD = "password-sintetica-test"
_HASH = hash_password(PASSWORD)  # una sola volta: argon2 è lento


def pytest_sessionstart(session):
    cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
    cfg.set_main_option("script_location", str(Path(__file__).parent.parent / "alembic"))
    command.upgrade(cfg, "head")


def pytest_sessionfinish(session, exitstatus):
    if _server:
        _server.cleanup()
        shutil.rmtree(_tmp, ignore_errors=True)
    shutil.rmtree(_arch, ignore_errors=True)
    shutil.rmtree(_temp, ignore_errors=True)


@pytest.fixture
def db():
    with get_sessionmaker()() as s:
        yield s


def _sfx() -> str:
    return uuid.uuid4().hex[:8]


@pytest.fixture
def crea_ufficio(db):
    def _crea(attivo=True) -> Ufficio:
        s = _sfx()
        u = Ufficio(codice=f"U{s}", nome=f"Ufficio sintetico {s}", attivo=attivo)
        db.add(u); db.commit()
        return u
    return _crea


@pytest.fixture
def crea_utente(db):
    def _crea(ruolo: Ruolo, ufficio: Ufficio | None = None, attivo=True) -> Utente:
        s = _sfx()
        u = Utente(username=f"{ruolo.value}_{s}", nome_visualizzato=f"Utente {s}", ruolo=ruolo,
                   ufficio_id=ufficio.id if ufficio else None, password_hash=_HASH, attivo=attivo)
        db.add(u); db.commit()
        return u
    return _crea


@pytest.fixture
def crea_pratica(db):
    def _crea(stato=Stato.DA_SMISTARE, ufficio: Ufficio | None = None) -> Pratica:
        s = _sfx()
        p = Pratica(numero=f"ESP-T-{s}", protocollo=f"P{s}/2025", tipo="esposto", titolo=f"Pratica sintetica {s}",
                    comune="Castelrovo", canale=Canale.caricamento_manuale, stato=stato,
                    ufficio_id=ufficio.id if ufficio else None)
        db.add(p); db.commit()
        return p
    return _crea


@pytest.fixture
def accedi():
    """Restituisce un client già autenticato come l'utente indicato."""
    def _accedi(utente: Utente) -> TestClient:
        c = TestClient(app, base_url="https://testserver")
        r = c.post("/api/v1/auth/login", json={"username": utente.username, "password": PASSWORD})
        assert r.status_code == 200, r.text
        return c
    return _accedi


@pytest.fixture
def anonimo() -> TestClient:
    return TestClient(app, base_url="https://testserver")


@pytest.fixture
def dir_temp():
    return Path(_temp)
