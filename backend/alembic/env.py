# alembic/env.py
from __future__ import annotations
import os
import sys
from logging.config import fileConfig
from sqlalchemy import create_engine, pool
from alembic import context

# load dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ensure project root is importable
HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.abspath(os.path.join(HERE, ".."))
GRANDPARENT = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in (PARENT, GRANDPARENT):
    if p not in sys.path:
        sys.path.insert(0, p)

config = context.config
fileConfig(config.config_file_name)

# get DB url from env
db_url = os.getenv("DATABASE_URL")

# import your Base (adjust if you use a different module)
try:
    from app.db.base import Base  # <- this should point to your Base
except Exception as e:
    raise RuntimeError("Failed to import Base from app.db.base: " + str(e))

target_metadata = Base.metadata

def run_migrations_offline():
    url = db_url or config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    if db_url:
        connectable = create_engine(db_url, poolclass=pool.NullPool)
    else:
        connectable = create_engine(config.get_main_option("sqlalchemy.url"), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
