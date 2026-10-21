"""coda e risultati del motore; numerazione delle pratiche

Revision ID: 0003
Revises: 0002
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE pratica_numero_seq")
    op.create_table(
        "lavoro_motore",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("documento_id", sa.Uuid, sa.ForeignKey("documento.id"), nullable=False),
        sa.Column("pratica_id", sa.Uuid, sa.ForeignKey("pratica.id"), nullable=False),
        sa.Column("stato", sa.Enum("in_coda", "in_corso", "completato", "errore", name="stato_lavoro",
                                   native_enum=False, length=32, create_constraint=True), nullable=False),
        sa.Column("tentativi", sa.Integer, nullable=False, server_default="0"),
        sa.Column("richiesto_da", sa.Uuid, sa.ForeignKey("utente.id")),
        sa.Column("richiesto_il", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("iniziato_il", sa.DateTime(timezone=True)),
        sa.Column("finito_il", sa.DateTime(timezone=True)),
        sa.Column("codice_errore", sa.String(64)),
    )
    op.create_index("ix_lavoro_motore_documento_id", "lavoro_motore", ["documento_id"])
    op.create_index("ix_lavoro_motore_pratica_id", "lavoro_motore", ["pratica_id"])
    op.create_index("ix_lavoro_coda", "lavoro_motore", ["stato", "richiesto_il"])
    op.create_table(
        "risultato_motore",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("lavoro_id", sa.Uuid, sa.ForeignKey("lavoro_motore.id"), nullable=False, unique=True),
        sa.Column("documento_id", sa.Uuid, sa.ForeignKey("documento.id"), nullable=False),
        sa.Column("pratica_id", sa.Uuid, sa.ForeignKey("pratica.id"), nullable=False),
        sa.Column("versione_motore", sa.String(64), nullable=False),
        sa.Column("versione_contratto", sa.String(16), nullable=False),
        sa.Column("tipo_documento", sa.String(64), nullable=False),
        sa.Column("tipo_documento_motivo", sa.Text),
        sa.Column("protocollo_letto", sa.String(64)),
        sa.Column("data_protocollo_letta", sa.Date),
        sa.Column("lettura_incerta", sa.Boolean, nullable=False),
        sa.Column("pagine_incerte", ARRAY(sa.Integer), nullable=False),
        sa.Column("acquisizione", JSONB, nullable=False),
        sa.Column("scheda", JSONB, nullable=False),
        sa.Column("proposta", JSONB, nullable=False),
        sa.Column("temi_proposti", JSONB, nullable=False),
        sa.Column("ricevuto_il", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_risultato_motore_documento_id", "risultato_motore", ["documento_id"])
    op.create_index("ix_risultato_motore_pratica_id", "risultato_motore", ["pratica_id"])


def downgrade() -> None:
    op.drop_table("risultato_motore")
    op.drop_table("lavoro_motore")
    op.execute("DROP SEQUENCE pratica_numero_seq")
