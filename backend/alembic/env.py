import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, text

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

db_url = os.environ.get("SYNC_DATABASE_URL", config.get_main_option("sqlalchemy.url"))
config.set_main_option("sqlalchemy.url", db_url)

from app.database import Base
from app.models import db_models  # noqa: F401

target_metadata = Base.metadata


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        connection.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        connection.commit()

        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()

        # IVFFlat index on rag_chunks embedding
        try:
            connection.execute(text(
                "CREATE INDEX IF NOT EXISTS rag_chunks_embedding_idx "
                "ON rag_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
            ))
            connection.commit()
        except Exception:
            pass


run_migrations_online()
