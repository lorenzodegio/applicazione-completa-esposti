"""python -m api.azzera: svuota pratiche e registro, lascia la configurazione, riprotegge il registro.

Il test lavora in una transazione che alla fine si annulla: il database di test degli altri test non cambia.
"""
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from api.azzera import RESTANO, TABELLE, azzera_database, conteggi, svuota_archivio
from api.enums import Ruolo
from api.registro import registra


def test_svuota_le_pratiche_e_lascia_uffici_utenti_temi(db, crea_ufficio, crea_utente, crea_pratica):
    uff = crea_ufficio()
    crea_utente(Ruolo.operatore, uff)
    p = crea_pratica(ufficio=uff)
    registra(db, utente_id=None, azione="pratica.crea", oggetto_tipo="pratica", oggetto_id=p.id, pratica_id=p.id)
    db.commit()
    engine = db.get_bind()
    db.close()

    with engine.connect() as conn:
        tx = conn.begin()
        try:
            restano_prima = conteggi(conn, RESTANO)
            assert conteggi(conn)["pratica"] >= 1 and conteggi(conn)["registro_azioni"] >= 1
            azzera_database(conn, riavvia_numerazione=False)
            assert conteggi(conn) == {t: 0 for t in TABELLE}
            assert conteggi(conn, RESTANO) == restano_prima          # uffici, utenti, temi... intatti
            assert restano_prima["tema"] >= 4 and restano_prima["voce_vocabolario"] > 0
            # il registro torna subito di sola aggiunta (una riga, perché il trigger di DELETE è per riga)
            s = Session(bind=conn)
            registra(s, utente_id=None, azione="sistema.azzera", oggetto_tipo="sistema")
            s.flush()
            for istruzione in ("TRUNCATE registro_azioni", "DELETE FROM registro_azioni"):
                sp = conn.begin_nested()
                with pytest.raises(DBAPIError, match="sola aggiunta"):
                    conn.execute(text(istruzione))
                sp.rollback()
        finally:
            tx.rollback()

    with engine.connect() as conn:   # niente è cambiato davvero
        assert conn.execute(text("SELECT count(*) FROM pratica WHERE id = :i"), {"i": p.id}).scalar_one() == 1


def test_svuota_archivio_cancella_il_contenuto_non_la_cartella(tmp_path):
    radice = tmp_path / "archivio"
    (radice / "2026" / "10").mkdir(parents=True)
    (radice / "2026" / "10" / "a.pdf").write_bytes(b"sintetico")
    (radice / "b.testo.json").write_text("{}")
    assert svuota_archivio(radice) == 2
    assert radice.is_dir() and not any(radice.iterdir())


def test_svuota_archivio_rifiuta_radici_sospette():
    with pytest.raises(SystemExit):
        svuota_archivio(Path("/"))
