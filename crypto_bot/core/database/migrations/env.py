from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
# For step 5, using MetaData directly for now
from sqlalchemy import MetaData


from alembic import context

# Import settings from the project
import os
import sys
# Add the project root to sys.path to allow for absolute imports
# Assuming env.py is in crypto_bot/core/database/migrations
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.settings.config import settings


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
# For now, as per instructions, set target_metadata to None or a new MetaData instance.
# We will define actual models later.
target_metadata = None # Or MetaData() if None causes issues with your Alembic version setup

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Use DATABASE_URL from settings for offline mode
    effective_url = settings.DATABASE_URL
    if not effective_url:
        raise ValueError("DATABASE_URL is not set in the environment or .env file for offline mode")
    
    context.configure(
        url=effective_url, # Use settings.DATABASE_URL
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Set the sqlalchemy.url from our settings
    effective_url = settings.DATABASE_URL
    if not effective_url:
        raise ValueError("DATABASE_URL is not set in the environment or .env file for online mode")

    # Get the Alembic Config object from the context
    alembic_config = context.config
    
    # Override the sqlalchemy.url from the .ini file with the one from settings
    alembic_config.set_main_option("sqlalchemy.url", effective_url)

    connectable = engine_from_config(
        alembic_config.get_section(alembic_config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
