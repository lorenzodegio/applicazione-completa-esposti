"""chiave del protocollo (numero + anno) per i collegamenti automatici

Un protocollo di sole cifre senza anno non deve unire pratiche di anni diversi: la chiave vale
«NUMERO/AAAA» con l'anno scritto nel protocollo o, se manca, quello di data_protocollo; senza anno è NULL.

Revision ID: 0006
Revises: 0005
"""
import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

CHIAVE = r"""CASE
  WHEN protocollo IS NULL OR btrim(protocollo) = '' THEN NULL
  WHEN btrim(protocollo) ~ '/\s*[0-9]{4}$' THEN regexp_replace(upper(btrim(protocollo)), '\s*/\s*', '/', 'g')
  WHEN data_protocollo IS NOT NULL THEN upper(btrim(protocollo)) || '/' || (extract(year FROM data_protocollo))::int::text
  ELSE NULL
END"""


def upgrade() -> None:
    op.add_column("pratica", sa.Column("chiave_protocollo", sa.String(80), sa.Computed(CHIAVE, persisted=True)))
    op.create_index("ix_pratica_chiave_protocollo", "pratica", ["chiave_protocollo"])


def downgrade() -> None:
    op.drop_index("ix_pratica_chiave_protocollo", table_name="pratica")
    op.drop_column("pratica", "chiave_protocollo")
