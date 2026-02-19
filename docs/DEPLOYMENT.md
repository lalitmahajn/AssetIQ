# AssetIQ Deployment Guide

This guide explains how to safely deploy updates to the AssetIQ application, with a focus on understanding the difference between code updates and database updates.

## Core Concept: Code vs. Data

It is critical to understand that **Docker images contain your code, but Volumes contain your data.**

1.  **Code (Docker Image)**: Contains `models.py`, `main.py`, and your application logic. When you run `docker compose build`, you are updating this blueprint.
2.  **Data (Postgres Volume)**: Contains the actual rows and tables of your live database. This persists even if you delete the container.

**The Disconnect**:
When you update `models.py` (Code), the live database (Data) does not automatically know about it. You must run a **Migration** to tell the database to update its structure to match your new code.

---

## Safe Deployment Checklist

Follow these steps to deploy changes to the live machine without losing data.

### 1. Get the Latest Code
Pull the latest changes from the repository.
```powershell
git pull origin main
```

### 2. Update the Containers
Rebuild and restart the containers to apply code changes.
**NOTE**: This is safe. It will NOT delete your database data because the volume is persistent.
```powershell
cd docker/plant
docker compose -f docker-compose.plant.yml up -d --build
```
*At this stage, your code is new, but your database structure is still old. The app might crash or error until the next step is done.*

### 3. Run Database Migrations (CRITICAL)
This command applies the structural changes (like renaming columns or adding tables) to the live database.
```powershell
docker compose -f docker-compose.plant.yml exec -e MIGRATION_TARGET=plant plant_backend alembic upgrade head
```

### 4. Verify
Check that the application is running correctly.
```powershell
docker compose -f docker-compose.plant.yml logs -f plant_backend
```

---

## Troubleshooting

### "Target database is not up to date"
If Alembic complains, it means the migration history in the database is out of sync.
**Fix**:
```powershell
docker compose -f docker-compose.plant.yml exec -e MIGRATION_TARGET=plant plant_backend alembic stamp head
```

### "Relation does not exist"
If you see this error in logs, it usually means you skipped Step 3 (Migration). The code is trying to access a table or column that doesn't exist in the database yet.
**Fix**: Run the migration command in Step 3.
