# AssetIQ (Plant Node + Optional HQ) — Customer Deployment Baseline

AssetIQ is an industrial Asset Management system designed for **Plant-first deployment**:

- **1 Plant = 1 Local Server** (Plant Node is mandatory)
- **HQ Aggregator is optional** (for multi-plant visibility)
- Notifications: **Email only**
- Timeline: **append-only truth**
- RUNNING state: **only via PLC feedback**
- Stop popup: **realtime + persistent Stop Queue**
- Shared PC rule: **Station identity ≠ Human user** (station token is not user auth)

For customer go-live steps, use **docs/README_RUNBOOK.md**.
## IMPORTANT: .env File Placement (Critical)

Docker Compose reads the `.env` file from the **directory where you run the command**.

### Option A (simple, recommended)
Place `.env` in the same folder where you run Docker Compose:

- Plant Node: put `.env` in `docker/plant/`
- HQ Node (optional): put `.env` in `docker/hq/`

If `.env` is placed elsewhere, Docker Compose will not load secrets and startup will fail.

### Common failure symptoms
- Compose error like:
  - `${JWT_SECRET:?set JWT_SECRET}`
  - `${PLANT_POSTGRES_PASSWORD:?set PLANT_POSTGRES_PASSWORD}`
- Containers exit immediately due to missing required secrets.


## What you will run

### Plant Node (mandatory)
- `plant_backend` (FastAPI)
- `plant_worker` (background jobs: email + sync + report vault)
- `postgres`
- `reverse_proxy` (nginx)
- `report_vault` volume

### HQ (optional)
- `hq_backend` (FastAPI receiver + APIs)
- `hq_worker`
- `postgres`
- `reverse_proxy` (nginx)

## Security model (high level)
- No default credentials.
- First admin is created only via **one-time bootstrap** using environment variables.
- Required secrets are env-based and the app **refuses to start** if missing.

## Next step
Open **docs/README_RUNBOOK.md** and follow:
- Required environment variables
- One-time admin bootstrap
- Docker compose boot
- Health checks
- Backup & restore
- Rollback
- Customer Production Go-Live Checklist

## Phase-2 (Enterprise) — HQ Multi-Plant View (Read-Only)

AssetIQ Phase-2 adds an optional HQ node for management visibility across multiple plants.

- Plant nodes remain local (1 plant = 1 server)
- HQ is read-only, visibility only
- Data sync is one-way: Plant → HQ (append-only, idempotent apply)

HQ Dashboard:
- `http://localhost:8100/hq/ui`

See **docs/README_RUNBOOK.md** for full HQ deployment steps.


## Commercial Editions
See **docs/COMMERCIAL_EDITIONS.md**, **docs/SALES_PITCH.md**, **docs/DEMO_FLOW.md**

### Phase-3 Intelligence (Optional Add-On)
Read-only insights and patterns based on historical data. No control, no automation.
See **docs/README_RUNBOOK.md** for enablement flags.
