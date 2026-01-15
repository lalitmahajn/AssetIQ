import os
from sqlalchemy import create_engine
from common_core.db import Base
# Import all models to register them with Base.metadata
from apps.hq_backend import models

def main():
    db_url = os.environ.get("HQ_DB_URL")
    # Fallback if not set in environment (but it should be in production) or construct from components
    if not db_url:
        print("HQ_DB_URL not found, constructing from components...")
        user = os.environ.get("HQ_POSTGRES_USER", "assetiq")
        password = os.environ.get("HQ_POSTGRES_PASSWORD", "assetiq_password_123")
        db_name = os.environ.get("HQ_POSTGRES_DB", "assetiq_hq")
        host = "hq_postgres" # Internal docker hostname
        port = "5432"
        db_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}"
    
    print(f"Connecting to: {db_url}")
    engine = create_engine(db_url)
    
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Schema creation complete.")

if __name__ == "__main__":
    main()
