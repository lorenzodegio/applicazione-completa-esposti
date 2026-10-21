"""registro di sola aggiunta; vocabolari e temi iniziali

Revision ID: 0002
Revises: 0001
"""
import uuid

import sqlalchemy as sa
from alembic import op

from api.dati_iniziali import AMBITO_STORICO, TEMI, VOCABOLARI

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Registro: niente UPDATE, DELETE né TRUNCATE, nemmeno per l'utente applicativo.
    # (In produzione si tolgono anche i privilegi UPDATE/DELETE all'utente del database.)
    op.execute("""
        CREATE FUNCTION registro_azioni_immutabile() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'registro_azioni è di sola aggiunta';
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""CREATE TRIGGER registro_azioni_no_modifiche BEFORE UPDATE OR DELETE
                  ON registro_azioni FOR EACH ROW EXECUTE FUNCTION registro_azioni_immutabile();""")
    op.execute("""CREATE TRIGGER registro_azioni_no_truncate BEFORE TRUNCATE
                  ON registro_azioni FOR EACH STATEMENT EXECUTE FUNCTION registro_azioni_immutabile();""")

    voce = sa.table("voce_vocabolario",
                    sa.column("id", sa.Uuid), sa.column("vocabolario", sa.String), sa.column("codice", sa.String),
                    sa.column("etichetta", sa.String), sa.column("ordine", sa.Integer), sa.column("attivo", sa.Boolean),
                    sa.column("elenco", sa.String), sa.column("converte_in", sa.String))
    righe = [dict(id=uuid.uuid4(), vocabolario=v, codice=c, etichetta=c, ordine=i, attivo=True,
                  elenco="attuale", converte_in=None)
             for v, voci in VOCABOLARI.items() for i, c in enumerate(voci)]
    righe += [dict(id=uuid.uuid4(), vocabolario="ambito", codice=c, etichetta=c, ordine=i, attivo=True,
                   elenco="storico", converte_in=nuovo)
              for i, (c, nuovo) in enumerate(AMBITO_STORICO.items())]
    op.bulk_insert(voce, righe)

    tema = sa.table("tema", sa.column("id", sa.Uuid), sa.column("codice", sa.String), sa.column("nome", sa.String),
                    sa.column("ordine", sa.Integer), sa.column("attivo", sa.Boolean))
    op.bulk_insert(tema, [dict(id=uuid.uuid4(), codice=c, nome=n, ordine=i, attivo=True)
                          for i, (c, n) in enumerate(TEMI)])


def downgrade() -> None:
    op.execute("DROP TRIGGER registro_azioni_no_truncate ON registro_azioni")
    op.execute("DROP TRIGGER registro_azioni_no_modifiche ON registro_azioni")
    op.execute("DROP FUNCTION registro_azioni_immutabile()")
    op.execute("DELETE FROM voce_vocabolario")
    op.execute("DELETE FROM tema")
