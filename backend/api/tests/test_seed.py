from sqlalchemy import func, select

from api.models import Pratica, Utente
from api.seed import esegui


def test_seed_ripetibile(db):
    esegui(db)
    n = db.execute(select(func.count()).select_from(Pratica)).scalar_one()
    assert esegui(db) is False
    assert db.execute(select(func.count()).select_from(Pratica)).scalar_one() == n
    assert db.execute(select(func.count()).select_from(Utente).where(Utente.username == "op.vet")).scalar_one() == 1
