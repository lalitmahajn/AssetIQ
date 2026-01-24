---
description: Database and Docker sync rules - ensures changes to models, migrations, and Docker stay consistent
---

# AssetIQ Database & Docker Sync Workflow

## When to Use This Workflow
Automatically follow these rules when making changes to:
- SQLAlchemy models (`apps/plant_backend/models.py` or `apps/hq_backend/models.py`)
- Alembic migrations (`alembic/versions/`)
- Docker configuration (`docker/plant/` or `docker/hq/`)
- Database-related features

---

## Rule 1: Model Changes → Create Migration

**If you modify `models.py` (add/remove/change columns or tables):**

1. Update the model in the appropriate `models.py` file
2. Create an Alembic migration:
   ```bash
   # For Plant changes:
   MIGRATION_TARGET=plant alembic revision --autogenerate -m "description_of_change"
   
   # For HQ changes:
   MIGRATION_TARGET=hq alembic revision --autogenerate -m "description_of_change"
   ```
3. Review the auto-generated migration for correctness
4. Remove any incorrect DROP statements for tables belonging to the other database (Plant vs HQ)

---

## Rule 2: New Tables → Verify init_db.py

**If you add a new table/model:**

1. Ensure it imports in the models.py file (for SQLAlchemy to register it)
2. Verify `init_db.py` will pick it up (it imports all models automatically)
3. No changes needed to init_db.py normally - it uses `Base.metadata.create_all()`

---

## Rule 3: Docker Entrypoint → Always Use init_db First

**The entrypoint startup order MUST be:**
1. `python -m apps.<backend>.init_db` (creates tables from models)
2. `alembic upgrade head` (applies migrations)
3. `uvicorn ...` (starts app)

**If modifying Dockerfiles or entrypoints:**
- Entrypoint must be in `/usr/local/bin/` (not `/app/` which gets volume-mounted)
- Use `ENTRYPOINT` directive, not `CMD`

---

## Rule 4: Migration Target Awareness

**Plant-only tables (MIGRATION_TARGET=plant):**
- users, stop_queue, plc_config, plc_tags, tickets, ticket_activities
- event_outbox, email_queue, whatsapp_queue, ingest_dedup, timeline_events
- audit_log, dead_letter, assets, master_types, master_items
- reason_suggestions, report_requests, stations, system_config

**HQ-only tables (MIGRATION_TARGET=hq):**
- hq_plants, applied_correlation, dead_letter, rollup_daily
- ticket_snapshot, hq_timeline_event, stop_reason_daily
- email_queue, report_job, hq_insight_daily, hq_users

**Never let auto-generated migrations DROP tables from the wrong database!**

---

## Rule 5: Testing Database Changes

**Before committing database changes:**

// turbo
1. Stop and remove containers with volumes:
   ```bash
   docker-compose -f docker/plant/docker-compose.plant.yml down -v
   ```

// turbo
2. Rebuild and start fresh:
   ```bash
   docker-compose -f docker/plant/docker-compose.plant.yml up -d --build
   ```

// turbo
3. Verify tables created:
   ```bash
   docker exec plant-postgres-1 psql -U assetiq -d assetiq_plant -c "\dt"
   ```

// turbo
4. Check backend logs for errors:
   ```bash
   docker logs plant-plant_backend-1
   ```

---

## Quick Reference Checklist

When making changes, verify:

- [ ] Model changes? → Create migration with correct MIGRATION_TARGET
- [ ] New table? → Ensure model is imported and registered with Base
- [ ] Migration auto-generated? → Check for incorrect DROP statements
- [ ] Dockerfile changed? → Entrypoint in /usr/local/bin, uses init_db
- [ ] Tested on fresh database? → down -v, up --build, verify tables
