"""Rinomina l'account demo dello smistatore.

Revision ID: 0007
Revises: 0006
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

VECCHIO_USERNAME = "smistatore"
NUOVO_USERNAME = "gestore_delle_pratiche"


def upgrade() -> None:
    conn = op.get_bind()
    vecchio = conn.execute(
        sa.text("SELECT id FROM utente WHERE username = :username"),
        {"username": VECCHIO_USERNAME},
    ).first()
    nuovo = conn.execute(
        sa.text("SELECT id FROM utente WHERE username = :username"),
        {"username": NUOVO_USERNAME},
    ).first()

    if vecchio and nuovo:
        raise RuntimeError(
            "Impossibile rinominare l'account: esistono già sia 'smistatore' "
            "sia 'gestore_delle_pratiche'. Risolvi il duplicato prima della migrazione."
        )
    if vecchio:
        conn.execute(
            sa.text("UPDATE utente SET username = :nuovo WHERE username = :vecchio"),
            {"nuovo": NUOVO_USERNAME, "vecchio": VECCHIO_USERNAME},
        )


def downgrade() -> None:
    conn = op.get_bind()
    nuovo = conn.execute(
        sa.text("SELECT id FROM utente WHERE username = :username"),
        {"username": NUOVO_USERNAME},
    ).first()
    vecchio = conn.execute(
        sa.text("SELECT id FROM utente WHERE username = :username"),
        {"username": VECCHIO_USERNAME},
    ).first()

    if nuovo and vecchio:
        raise RuntimeError(
            "Impossibile annullare la rinomina: esistono già entrambi gli username."
        )
    if nuovo:
        conn.execute(
            sa.text("UPDATE utente SET username = :vecchio WHERE username = :nuovo"),
            {"nuovo": NUOVO_USERNAME, "vecchio": VECCHIO_USERNAME},
        )
