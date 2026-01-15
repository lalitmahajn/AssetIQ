# AssetIQ — README_RUNBOOK (Customer Production Go-Live)

## IMPORTANT: .env File Placement (Critical)

Docker Compose loads `.env` from the **current working directory** (the directory where you execute `docker compose ...`).

### Recommended (Option A)
- Plant Node: place `.env` inside `docker/plant/`
- HQ Node (optional): place `.env` inside `docker/hq/`

If `.env` is placed at repository root or any other folder, Docker Compose may not load required secrets and startup will fail.

### Common failure symptoms
- Compose errors:
  - `${JWT_SECRET:?set JWT_SECRET}`
  - `${SYNC_HMAC_SECRET:?set SYNC_HMAC_SECRET}`
  - `${STATION_SECRET_ENC_KEY:?set STATION_SECRET_ENC_KEY}`
  - `${PLANT_POSTGRES_PASSWORD:?set PLANT_POSTGRES_PASSWORD}`
- Services exit on startup complaining required secrets are missing.


This runbook is written for **Customer IT / Ops** teams.
It is safe for production rollout (no demo credentials, no default secrets).

---

## 1) Prerequisites
- Docker Desktop / Docker Engine + Docker Compose plugin installed
- Ports available:
  - Plant Backend: `8000` (HTTP)
  - Plant Reverse Proxy: `8080` (HTTP)
  - Plant UI: `5173` (HTTP)
  - HQ Backend (optional): `8100` (HTTP)
  - HQ Reverse Proxy (optional): `8081` (HTTP)

> Production note: reverse proxy configs are **TLS-ready** (terminate TLS at nginx or upstream load balancer).

---

## 2) REQUIRED environment variables (MUST SET)

Create a `.env` file (recommended) or export env vars in your shell.

### Required secrets (NO DEFAULTS)
```env
JWT_SECRET=put_a_32_plus_char_secret_here________________
SYNC_HMAC_SECRET=put_a_32_plus_char_secret_here________________
STATION_SECRET_ENC_KEY=put_a_32_plus_char_secret_here________________
```

### Required DB passwords
```env
PLANT_POSTGRES_PASSWORD=strong_db_password_here
# Only if HQ is used:
HQ_POSTGRES_PASSWORD=strong_db_password_here
```

### Optional: site code
```env
PLANT_SITE_CODE=P01
```

#### Intentional startup enforcement
- If any required secret is missing, **AssetIQ will refuse to start**.
- This is intentional security behavior for commercial go-live.

---

## 3) One-time Admin Bootstrap (MANDATORY FIRST RUN)

AssetIQ does **not** ship any default admin user.

On the first run, you must provide the bootstrap environment variables:

```env
BOOTSTRAP_ADMIN_EMAIL=admin@company.com
BOOTSTRAP_ADMIN_PIN=strong_pin_min_6_not_common
```

### Bootstrap rules (IMPORTANT)
- Runs **only if no user exists** in the database.
- If a user already exists, bootstrap is **skipped** (one-time only).
- Weak PINs are rejected (examples): `0000`, `1111`, repeating digits, simple sequences, etc.
- PIN is hashed with **bcrypt**.

> After bootstrap is completed, you may remove `BOOTSTRAP_ADMIN_*` from your environment.

---

## 4) Start Plant Node (MANDATORY)

From repository root:

```bash
cd docker/plant
# IMPORTANT: ensure .env is placed in this folder (docker/plant/)
docker compose -f docker-compose.plant.yml up -d --build
```

### Health checks (must return HTTP 200)
```bash
curl -s -o /dev/null -w "%{http_code}
" http://localhost:8000/healthz
curl -s -o /dev/null -w "%{http_code}
" http://localhost:8000/readyz
```

### View logs
```bash
docker compose -f docker-compose.plant.yml logs -f plant_backend
docker compose -f docker-compose.plant.yml logs -f plant_worker
```

Expected worker log includes: `worker_started`

---

## 5) Optional: Start HQ (for multi-plant aggregation)

```bash
cd docker/hq
# IMPORTANT: ensure .env is placed in this folder (docker/hq/)
docker compose -f docker-compose.hq.yml up -d --build
```

HQ health checks:
```bash
curl -s -o /dev/null -w "%{http_code}
curl -s -o /dev/null -w "%{http_code}
" http://localhost:8100/healthz
curl -s -o /dev/null -w "%{http_code}
" http://localhost:8100/readyz
```

### HQ Dashboard (via proxy)
- `http://localhost:8081` (redirects to `/hq/ui`)
```

---

## 6) Login (after bootstrap)

After bootstrap completed, login via API (example):

```bash
curl -s http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@company.com","pin":"<YOUR_PIN>"}'
```

Rate limiting is enabled. Repeated wrong PIN attempts will return HTTP `429`.

---

## 7) Backup & Restore (customer IT)

### Backup (Plant DB)
```bash
docker exec -t $(docker ps -q --filter "name=postgres" | head -n 1) pg_dump -U assetiq -d assetiq_plant > plant_backup.sql
```

### Restore (Plant DB)
```bash
cat plant_backup.sql | docker exec -i $(docker ps -q --filter "name=postgres" | head -n 1) psql -U assetiq -d assetiq_plant
```

> If you run both Plant and HQ on the same host, use container names from `docker ps` to avoid ambiguity.

---

## 8) Rollback (safe procedure)
1) Stop current version:
```bash
cd docker/plant
docker compose -f docker-compose.plant.yml down
```
2) Restore DB backup if required (see Backup & Restore).
3) Start the **previous known-good ZIP** version.
4) Verify:
- `/healthz` returns 200
- `/readyz` returns 200

---


## 5-Minute Go-Live Verification (Plant Node)

```bash
cd docker/plant
# Ensure .env is present in this folder (IMPORTANT section above)
docker compose -f docker-compose.plant.yml up -d --build
```

Health (expected HTTP 200):
```bash
curl -s -o /dev/null -w "%{http_code}
" http://localhost:8000/healthz
curl -s -o /dev/null -w "%{http_code}
" http://localhost:8000/readyz
```

Worker log (expected: `worker_started`):
```bash
docker compose -f docker-compose.plant.yml logs -f plant_worker
```

## 9) Customer Production Go-Live Checklist

### Secrets & access
- [ ] `JWT_SECRET`, `SYNC_HMAC_SECRET`, `STATION_SECRET_ENC_KEY` prepared (32+ chars)
- [ ] DB passwords set (`PLANT_POSTGRES_PASSWORD`, optional `HQ_POSTGRES_PASSWORD`)
- [ ] Secrets stored in customer-approved secret store (Vault/KMS/.env with restricted access)

### Bootstrap
- [ ] `BOOTSTRAP_ADMIN_EMAIL` and strong `BOOTSTRAP_ADMIN_PIN` set for first run
- [ ] Admin bootstrap completed (only once)
- [ ] Bootstrap env vars removed after first successful admin creation

### Runtime checks
- [ ] Plant services up (`docker compose ps`)
- [ ] Health checks:
  - [ ] `http://localhost:8000/healthz` = 200
  - [ ] `http://localhost:8000/readyz` = 200
- [ ] Plant UI accessible: `http://localhost:5173`
- [ ] Worker running and logs `worker_started`
- [ ] Login verified (rate limit works)

### Backup / restore
- [ ] Backup script verified (plant DB dump created)
- [ ] Restore verified in a staging sandbox

### Rollback readiness
- [ ] Previous ZIP version retained for rollback
- [ ] Rollback steps understood and tested

### Operations & support
- [ ] SMTP route configured (if used)
- [ ] Support contact defined (customer internal + vendor escalation path)
- [ ] Monitoring plan decided (log collection + container restart policy)

---

## 10) Common Deployment Errors (quick fixes)

### A) Missing secrets
**Symptom:** service exits on startup, error shows required secret missing.  
**Fix:** set required env vars and restart compose.

### B) Weak PIN rejected
**Symptom:** bootstrap fails with “PIN is too weak”.  
**Fix:** use a stronger PIN (min 6, avoid common sequences like 0000/1111/repeating digits).

### C) DB password missing
**Symptom:** docker compose fails with `${PLANT_POSTGRES_PASSWORD:? ...}` error.  
**Fix:** set `PLANT_POSTGRES_PASSWORD` (and `HQ_POSTGRES_PASSWORD` if HQ is used).

## Phase-2 (Enterprise) — HQ Multi-Plant Management View (Read-Only)

Phase-2 adds a **central HQ node** for visibility and reporting across multiple plants.
**Plant servers stay unchanged. HQ is read-only and cannot control plants.**

### HQ Node — Quick Start

1) Create the HQ environment file

Place the file here (critical):
- `docker/hq/.env`

Minimum required (example):
```env
# Required secrets (NO DEFAULTS)
JWT_SECRET=your_32_plus_char_secret_here
SYNC_HMAC_SECRET=your_32_plus_char_secret_here
STATION_SECRET_ENC_KEY=your_32_plus_char_secret_here

# HQ DB
HQ_POSTGRES_PASSWORD=strong_password_here

# Email (for reports / dead-letter alerts)
SMTP_HOST=smtp.yourcompany.com
SMTP_PORT=587
SMTP_USER=alerts@yourcompany.com
SMTP_PASS=your_smtp_password
SMTP_FROM=AssetIQ Alerts <alerts@yourcompany.com>
EMAIL_IT=it-alerts@yourcompany.com
```

2) Start HQ
```bash
cd docker/hq
docker compose up -d --build
```

3) HQ health checks
```bash
curl http://localhost:8100/healthz
curl http://localhost:8100/readyz
```

Expected:
- both return `200`

4) Open HQ dashboard (read-only)
- Nginx Proxy (Recommended): `http://localhost:8081`
- Direct Backend: `http://localhost:8100/hq/ui`

### Plant → HQ Sync (One-way)

- Data flow is **Plant → HQ only**
- HQ applies sync items **idempotently** using `correlation_id`
- Failed items go to `dead_letter` and trigger an IT email (via HQ email_queue)

Plant nodes must be configured to point to HQ receiver:
- `HQ_RECEIVER_URL=http://hq_backend:8100/sync/receive` (docker-to-docker)
- or the correct reachable URL if running across networks.

### HQ Reports (Vault)

HQ reports are generated by the HQ worker and stored here:
- `report_vault/hq/`

Reports generated:
- DAILY (yesterday UTC)
- WEEKLY (last 7 days ending yesterday UTC)
- MONTHLY (previous calendar month UTC)

List generated reports:
- `GET http://localhost:8100/hq/reports/list`


## Phase-3 Intelligence (Read-only Insights) — Optional Add-On

**What it is:** daily insights based on historical data (patterns and summaries).  
**What it is NOT:** no control, no PLC write-back, no automation, no prediction guarantees.

### Enable / Disable
Phase-3 is **disabled by default**. To enable in HQ:

```env
ENABLE_INTELLIGENCE=true
INTELLIGENCE_WINDOW_DAYS=14
```

Optional weekly email digest (opt-in):

```env
ENABLE_INTELLIGENCE_DIGEST=true
INTELLIGENCE_DIGEST_TO=maintenance.head@company.com
```

### Labels in UI and Reports
Insights are shown as **“Insight” / “Pattern Observed”** (read-only).  
If data is insufficient, UI shows **“Not enough data yet”**.
