import datetime as dt

from sqlalchemy import text
from sqlalchemy.orm import Session


def prossimo_numero(db: Session) -> str:
    n = db.execute(text("SELECT nextval('pratica_numero_seq')")).scalar_one()
    return f"ESP-{dt.date.today().year}-{n:06d}"
