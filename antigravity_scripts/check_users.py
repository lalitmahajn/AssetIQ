from common_core.db import PlantSessionLocal
from apps.plant_backend.models import User

def main():
    db = PlantSessionLocal()
    try:
        users = db.query(User).all()
        print(f"Total Users: {len(users)}")
        for u in users:
            print(f"User: {u.id}, Roles: {u.roles}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
