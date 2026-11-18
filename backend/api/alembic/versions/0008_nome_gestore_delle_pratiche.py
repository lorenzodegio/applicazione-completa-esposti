"""Aggiorna il nominativo visualizzato dell'account gestore delle pratiche.

Revision ID: 0008
Revises: 0007
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE utente "
            "SET nome_visualizzato = 'Sara Gestore' "
            "WHERE username = 'gestore_delle_pratiche' "
            "AND nome_visualizzato IN ("
            "'Sara Smistatrice', 'Sara Smistatrice (sintetica)')"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE utente "
            "SET nome_visualizzato = 'Sara Smistatrice (sintetica)' "
            "WHERE username = 'gestore_delle_pratiche' "
            "AND nome_visualizzato = 'Sara Gestore'"
        )
    )
