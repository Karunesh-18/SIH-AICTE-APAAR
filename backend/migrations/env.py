from alembic import context
from sqlalchemy import create_engine

import app.models  # noqa: F401  (registers all tables)
from app.core.config import settings
from app.db.base import Base

config = context.config
target_metadata = Base.metadata


def _url() -> str:
    # Tests and scripts can override with sqlalchemy.url; otherwise use app settings.
    return config.get_main_option("sqlalchemy.url") or settings.database_url


def run_migrations_offline() -> None:
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True,
                      render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_url())
    with engine.connect() as conn:
        # batch mode lets SQLite alter tables; harmless on Postgres
        context.configure(connection=conn, target_metadata=target_metadata,
                          render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
