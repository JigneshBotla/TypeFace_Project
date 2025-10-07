# create_tables.py — run once to create missing tables/columns (development helper)
from app.db.session import engine
from app.db.base import Base
import logging, sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("Creating tables in the database (if not exist)...")
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Done.")
except Exception as e:
    logger.exception("Error creating tables:")
    sys.exit(1)
