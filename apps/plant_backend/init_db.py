"""
Database initialization script for Plant backend.
Creates all tables from SQLAlchemy models if they don't exist.
Safe to run multiple times - create_all() is idempotent.
"""

from __future__ import annotations

import logging
import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_plant_db() -> None:
    """Initialize Plant database tables from SQLAlchemy models."""
    from sqlalchemy import create_engine, text

    # Import models to register them with Base.metadata
    from apps.plant_backend import models  # noqa: F401
    from common_core.db import Base

    # Get database URL from environment
    db_url = os.environ.get("PLANT_DB_URL")
    if not db_url:
        logger.error("PLANT_DB_URL environment variable not set")
        sys.exit(1)

    logger.info("Connecting to Plant database...")
    engine = create_engine(db_url, pool_pre_ping=True)

    # Test connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        sys.exit(1)

    # Create all tables that don't exist
    logger.info("Creating tables from SQLAlchemy models...")
    logger.info(f"Models registered: {list(Base.metadata.tables.keys())}")

    Base.metadata.create_all(engine)

    logger.info("Plant database initialization complete!")


if __name__ == "__main__":
    init_plant_db()
