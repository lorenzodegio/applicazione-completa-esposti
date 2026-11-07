"""controllo di versione della valutazione

Revision ID: 0005
Revises: 0004
"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("valutazione", sa.Column("versione", sa.Integer, nullable=False, server_default="1"))


def downgrade() -> None:
    op.drop_column("valutazione", "versione")
