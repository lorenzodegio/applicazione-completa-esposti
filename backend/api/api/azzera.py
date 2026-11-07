"""Ripartire da zero: python -m api.azzera [--conferma]

Svuota pratiche, documenti (con l'archivio), lavori e risultati del motore, valutazioni, temi
delle pratiche, attività, collegamenti, assegnazioni, cambi di stato, note e registro delle
azioni; rimette a 1 la numerazione delle pratiche. Restano: uffici, utenti, sessioni, temi,
vocabolari e tipi di collegamento.

Senza --conferma mostra solo i conteggi e non tocca nulla. Solo con ESPOSTI_AMBIENTE=sviluppo.
Il registro è di sola aggiunta: i suoi trigger si disattivano e riattivano nella stessa transazione
dello svuotamento, e la prima riga del registro nuovo dice che è stato azzerato (chi: il sistema).
Prima di lanciarlo va fermato il worker (docker compose stop worker): vedi docs/avvio.md.
"""
import argparse
import shutil
from pathlib import Path

from sqlalchemy import Connection, create_engine, text

from .config import get_settings
from .registro import registra

# Tutte le tabelle legate alle pratiche (uno solo TRUNCATE: si riferiscono l'una all'altra).
TABELLE = ["registro_azioni", "nota_interna", "cambio_stato", "assegnazione", "collegamento", "attivita",
           "pratica_tema", "valutazione", "risultato_motore", "lavoro_motore", "documento", "pratica"]
RESTANO = ["ufficio", "utente", "sessione", "tema", "voce_vocabolario", "tipo_collegamento"]
TRIGGER_REGISTRO = ["registro_azioni_no_truncate", "registro_azioni_no_modifiche"]


def conteggi(conn: Connection, tabelle: list[str] = TABELLE) -> dict[str, int]:
    return {t: conn.execute(text(f"SELECT count(*) FROM {t}")).scalar_one() for t in tabelle}


def azzera_database(conn: Connection, *, riavvia_numerazione: bool = True) -> None:
    """Svuota le tabelle delle pratiche dentro la transazione di `conn` (non fa commit)."""
    for t in TRIGGER_REGISTRO:
        conn.execute(text(f"ALTER TABLE registro_azioni DISABLE TRIGGER {t}"))
    conn.execute(text(f"TRUNCATE {', '.join(TABELLE)}" + (" RESTART IDENTITY" if riavvia_numerazione else "")))
    for t in TRIGGER_REGISTRO:
        conn.execute(text(f"ALTER TABLE registro_azioni ENABLE TRIGGER {t}"))
    if riavvia_numerazione:
        conn.execute(text("ALTER SEQUENCE pratica_numero_seq RESTART WITH 1"))


def file_archivio(radice: Path) -> int:
    return sum(1 for p in radice.rglob("*") if p.is_file()) if radice.exists() else 0


def svuota_archivio(radice: Path) -> int:
    """Cancella tutto il contenuto della cartella dell'archivio (non la cartella). Restituisce i file cancellati."""
    radice = radice.expanduser().resolve()
    if radice in (Path("/"), Path.home().resolve()) or len(radice.parts) < 3:
        raise SystemExit(f"Radice dell'archivio sospetta, non la svuoto: {radice}")
    n = file_archivio(radice)
    for figlio in radice.iterdir() if radice.exists() else []:
        if figlio.is_dir() and not figlio.is_symlink():
            shutil.rmtree(figlio)
        else:
            figlio.unlink()
    return n


def main() -> None:
    ap = argparse.ArgumentParser(description="Svuota pratiche, documenti, archivio e registro (solo sviluppo).")
    ap.add_argument("--conferma", action="store_true", help="svuota davvero; senza, mostra solo i conteggi")
    args = ap.parse_args()
    cfg = get_settings()
    if cfg.ambiente != "sviluppo":
        raise SystemExit("python -m api.azzera gira solo con ESPOSTI_AMBIENTE=sviluppo")
    radice = Path(cfg.archivio_radice).expanduser()
    engine = create_engine(cfg.database_url)
    with engine.begin() as conn:
        prima = conteggi(conn)
        restano = conteggi(conn, RESTANO)
        in_corso = conn.execute(text("SELECT count(*) FROM lavoro_motore WHERE stato = 'in_corso'")).scalar_one()
        print("Da svuotare:")
        for t, n in prima.items():
            print(f"  {t:<18} {n}")
        print(f"  archivio            {file_archivio(radice)} file in {radice}")
        print("Restano: " + ", ".join(f"{t} {n}" for t, n in restano.items()))
        if not args.conferma:
            print("\nNessuna modifica. Per svuotare: python -m api.azzera --conferma (con il worker fermo).")
            return
        if in_corso:
            print(f"\nAttenzione: {in_corso} lavori risultano «in corso»: se il worker è acceso, fermalo prima.")
        azzera_database(conn)
    n = svuota_archivio(radice)
    from .db import get_sessionmaker
    with get_sessionmaker()() as db:
        registra(db, utente_id=None, azione="sistema.azzera", oggetto_tipo="sistema", oggetto_id=None,
                 dettagli={"righe": prima, "file_archivio": n})
        db.commit()
    print(f"\nFatto: svuotate {len(TABELLE)} tabelle ({sum(prima.values())} righe) e {n} file dell'archivio; "
          "numerazione delle pratiche ripartita da 1.")


if __name__ == "__main__":
    main()
