from alembic import context
from sqlalchemy import create_engine

from api.config import get_settings
from api.models import Base

target_metadata = Base.metadata


def run_migrations_online() -> None:
    url = context.get_x_argument(as_dictionary=True).get("url") or get_settings().database_url
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
