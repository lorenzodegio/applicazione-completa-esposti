"""valutazione, temi della pratica, attività, collegamenti; viste di analisi e disaccordo

Revision ID: 0004
Revises: 0003
"""
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def _enum(nome, *valori):
    return sa.Enum(*valori, name=nome, native_enum=False, length=32, create_constraint=True)


def upgrade() -> None:
    op.create_table(
        "valutazione",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("pratica_id", sa.Uuid, sa.ForeignKey("pratica.id"), nullable=False, unique=True),
        sa.Column("origine", _enum("origine_valutazione", "applicazione", "import_ats"), nullable=False),
        sa.Column("autore_id", sa.Uuid, sa.ForeignKey("utente.id")),
        sa.Column("autore_nome", sa.String(200)),
        sa.Column("compilata", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("data_compilazione", sa.Date),
        sa.Column("data_doc", sa.Date),
        sa.Column("comune", sa.String(200)),
        sa.Column("ambito", ARRAY(sa.Text), nullable=False, server_default="{}"),
        sa.Column("problematica", ARRAY(sa.Text), nullable=False, server_default="{}"),
        sa.Column("elementi", ARRAY(sa.Text), nullable=False, server_default="{}"),
        sa.Column("ambito_originale", ARRAY(sa.Text)),
        sa.Column("ambito_altro", sa.Text),
        sa.Column("problematica_altro", sa.Text),
        sa.Column("elementi_altro", sa.Text),
        sa.Column("esito", sa.String(100)),
        sa.Column("urgenza", sa.String(100)),
        sa.Column("azione", ARRAY(sa.Text), nullable=False, server_default="{}"),
        sa.Column("note", sa.Text),
        sa.Column("da_risultato_id", sa.Uuid, sa.ForeignKey("risultato_motore.id")),
        sa.Column("creata_il", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("aggiornata_il", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "pratica_tema",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("pratica_id", sa.Uuid, sa.ForeignKey("pratica.id"), nullable=False),
        sa.Column("tema_id", sa.Uuid, sa.ForeignKey("tema.id"), nullable=False),
        sa.Column("origine", _enum("origine_tema", "ia", "operatore"), nullable=False),
        sa.Column("stato", _enum("stato_tema", "proposto", "confermato", "scartato"), nullable=False),
        sa.Column("deciso_da", sa.Uuid, sa.ForeignKey("utente.id")),
        sa.Column("deciso_il", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("pratica_id", "tema_id"),
    )
    op.create_index("ix_pratica_tema_pratica_id", "pratica_tema", ["pratica_id"])
    op.create_index("ix_pratica_tema_tema_id", "pratica_tema", ["tema_id"])
    op.create_table(
        "attivita",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("pratica_id", sa.Uuid, sa.ForeignKey("pratica.id"), nullable=False),
        sa.Column("tipo", sa.String(100), nullable=False),
        sa.Column("stato", _enum("stato_attivita", "prevista", "in_corso", "conclusa", "annullata"), nullable=False),
        sa.Column("data_prevista", sa.Date),
        sa.Column("data_conclusione", sa.Date),
        sa.Column("descrizione", sa.Text),
        sa.Column("creata_da", sa.Uuid, sa.ForeignKey("utente.id"), nullable=False),
        sa.Column("creata_il", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("aggiornata_il", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_attivita_pratica_id", "attivita", ["pratica_id"])
    op.create_table(
        "tipo_collegamento",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("codice", sa.String(32), nullable=False, unique=True),
        sa.Column("etichetta", sa.String(100), nullable=False),
        sa.Column("etichetta_inversa", sa.String(100)),
        sa.Column("manuale", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "collegamento",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("pratica_da_id", sa.Uuid, sa.ForeignKey("pratica.id"), nullable=False),
        sa.Column("pratica_a_id", sa.Uuid, sa.ForeignKey("pratica.id"), nullable=False),
        sa.Column("tipo_id", sa.Uuid, sa.ForeignKey("tipo_collegamento.id"), nullable=False),
        sa.Column("nota", sa.Text),
        sa.Column("creato_da", sa.Uuid, sa.ForeignKey("utente.id"), nullable=False),
        sa.Column("creato_il", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("rimosso_da", sa.Uuid, sa.ForeignKey("utente.id")),
        sa.Column("rimosso_il", sa.DateTime(timezone=True)),
        sa.CheckConstraint("pratica_da_id <> pratica_a_id", name="ck_collegamento_diverse"),
    )
    op.create_index("ix_collegamento_pratica_da_id", "collegamento", ["pratica_da_id"])
    op.create_index("ix_collegamento_pratica_a_id", "collegamento", ["pratica_a_id"])
    op.create_index("uq_collegamento_attivo", "collegamento", ["pratica_da_id", "pratica_a_id", "tipo_id"],
                    unique=True, postgresql_where=sa.text("rimosso_il IS NULL"))

    tipi = sa.table("tipo_collegamento", sa.column("id", sa.Uuid), sa.column("codice", sa.String),
                    sa.column("etichetta", sa.String), sa.column("etichetta_inversa", sa.String),
                    sa.column("manuale", sa.Boolean))
    op.bulk_insert(tipi, [
        dict(id=uuid.uuid4(), codice="DUPLICATO", etichetta="Duplicato di", etichetta_inversa=None, manuale=True),
        dict(id=uuid.uuid4(), codice="INTEGRAZIONE", etichetta="Integra", etichetta_inversa="Integrata da", manuale=True),
        dict(id=uuid.uuid4(), codice="SEGUITO", etichetta="Seguito di", etichetta_inversa="Ha come seguito", manuale=True),
        dict(id=uuid.uuid4(), codice="CORRELATA", etichetta="Correlata a", etichetta_inversa=None, manuale=True),
        dict(id=uuid.uuid4(), codice="RISCONTRO", etichetta="Riscontro di", etichetta_inversa="Ha come riscontro", manuale=True),
        dict(id=uuid.uuid4(), codice="STESSO_PROTOCOLLO", etichetta="Stesso protocollo", etichetta_inversa=None, manuale=False),
    ])

    # Ultima analisi del documento principale di ogni pratica.
    op.execute("""
        CREATE VIEW pratica_analisi_principale AS
        SELECT p.id AS pratica_id, r.id AS risultato_id, r.lettura_incerta, r.ricevuto_il
        FROM pratica p
        JOIN LATERAL (SELECT rm.id, rm.lettura_incerta, rm.ricevuto_il FROM risultato_motore rm
                      WHERE rm.documento_id = p.documento_principale_id
                      ORDER BY rm.ricevuto_il DESC, rm.id LIMIT 1) r ON true
    """)
    # Disaccordo IA–operatore: valutazione compilata contro proposta del documento principale,
    # su esito, urgenza e insieme delle azioni (piano 3.5). Unica definizione: la usano elenco e dettaglio.
    op.execute("""
        CREATE VIEW pratica_disaccordo AS
        SELECT x.pratica_id, x.diff_esito, x.diff_urgenza, x.diff_azione,
               (x.diff_esito OR x.diff_urgenza OR x.diff_azione) AS in_disaccordo
        FROM (
            SELECT p.id AS pratica_id,
                   v.esito IS DISTINCT FROM (rm.proposta->>'esito') AS diff_esito,
                   v.urgenza IS DISTINCT FROM (rm.proposta->>'urgenza') AS diff_urgenza,
                   ARRAY(SELECT a FROM unnest(v.azione) AS a ORDER BY a)
                     IS DISTINCT FROM ARRAY(SELECT e FROM jsonb_array_elements_text(rm.proposta->'azione') AS e ORDER BY e)
                     AS diff_azione
            FROM pratica p
            JOIN valutazione v ON v.pratica_id = p.id AND v.compilata
            JOIN pratica_analisi_principale ap ON ap.pratica_id = p.id
            JOIN risultato_motore rm ON rm.id = ap.risultato_id
        ) x
    """)


def downgrade() -> None:
    op.execute("DROP VIEW pratica_disaccordo")
    op.execute("DROP VIEW pratica_analisi_principale")
    for t in ("collegamento", "tipo_collegamento", "attivita", "pratica_tema", "valutazione"):
        op.drop_table(t)
