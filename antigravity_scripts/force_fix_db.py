
from common_core.db import plant_engine, Base
# Import all models to ensure they are registered with Base
from apps.plant_backend import models

def fix():
    print("Forcing creation of all tables...")
    try:
        Base.metadata.create_all(bind=plant_engine)
        print("Tables created successfully.")
    except Exception as e:
        print(f"Error creating tables: {e}")

if __name__ == "__main__":
    fix()
