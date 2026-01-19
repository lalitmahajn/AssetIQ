import os
import sys

# Add project root to sys.path
sys.path.append(os.getcwd())

from sqlalchemy import text

from common_core.db import PlantSessionLocal


def migrate():
    db = PlantSessionLocal()
    try:
        print("Migrating: Adding is_critical to assets table...")
        # Check if column exists to avoid error
        try:
            db.execute(text("SELECT is_critical FROM assets LIMIT 1"))
            print("Column 'is_critical' already exists.")
        except Exception:
            print("Column not found. Adding it...")
            db.rollback()  # Reset transaction
            # SQLite syntax vs Postgres syntax. Assuming Postgres based on file structure, but let's try standard SQL.
            # Postgres: ALTER TABLE assets ADD COLUMN is_critical BOOLEAN DEFAULT FALSE NOT NULL;
            # SQLite: ALTER TABLE assets ADD COLUMN is_critical BOOLEAN DEFAULT 0 NOT NULL;
            # We'll try generic/Postgres first.
            try:
                db.execute(
                    text("ALTER TABLE assets ADD COLUMN is_critical BOOLEAN DEFAULT FALSE NOT NULL")
                )
                db.commit()
                print("Column added successfully.")
            except Exception as e:
                print(f"Migration failed: {e}")
                db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
