from sqlalchemy import create_engine, inspect
import os

# Use local port 5435 mapped to 5432
db_url = "postgresql+psycopg2://assetiq:assetiq_password_123@localhost:5435/assetiq_plant"
engine = create_engine(db_url)
insp = inspect(engine)

if "assets" in insp.get_table_names():
    print("SUCCESS: assets table exists")
    cols = [c["name"] for c in insp.get_columns("assets")]
    print(f"Columns: {cols}")
else:
    print("FAILURE: assets table missing")
