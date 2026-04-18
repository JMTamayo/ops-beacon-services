from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.config.conf import CONFIG
from app.models.base import Base
from app.models import device as _device  # noqa: F401
from app.models import device_entity_assignment as _device_entity_assignment  # noqa: F401
from app.models import entity as _entity  # noqa: F401
from app.models import measurement as _measurement  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = CONFIG.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(CONFIG.DATABASE_URL, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
