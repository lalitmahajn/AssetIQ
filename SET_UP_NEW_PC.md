# AssetIQ — New PC Setup Guide

Follow these steps to deploy AssetIQ (Plant + HQ) on a fresh machine.

## 1. Prerequisites
- **Git**
- **Docker Desktop** (with Compose)
- **Node.js** (optional, for local frontend dev)
- **Python 3.11** (optional, for local backend dev)

## 2. Environment Configuration
AssetIQ requires specific `.env` files to be placed in the Docker directories.

### Plant Node Setup
1. Create `docker/plant/.env`
2. Add the following required variables:
```env
# Required Secrets (32+ chars)
JWT_SECRET=your_32_char_random_secret_here
SYNC_HMAC_SECRET=your_32_char_hmac_secret_here
STATION_SECRET_ENC_KEY=your_32_char_enc_key_here

# Database
PLANT_POSTGRES_PASSWORD=strong_db_password_123

# Initial Admin Bootstrap (runs only on first boot)
BOOTSTRAP_ADMIN_EMAIL=admin@yourcompany.com
BOOTSTRAP_ADMIN_PIN=12345678 (min 6 characters)

# Network Access (Remote IP)
# If you want to access the UI from another PC in the same network, 
# set this to the IP of the server machine:
PLANT_API_BASE=http://<SERVER_IP>:8000
```

### HQ Aggregator (Optional)
If you need multi-plant visibility:
1. Create `docker/hq/.env`
2. Add similar secrets and `HQ_POSTGRES_PASSWORD`.

## 3. Launching the Services

Before starting the containers, you **must** create the shared Docker network:
```bash
docker network create assetiq_net
```

Open a terminal in the project root and run:

### Start Plant
```bash
cd docker/plant
docker compose -f docker-compose.plant.yml up -d --build
```

### Start HQ
```bash
cd docker/hq
docker compose -f docker-compose.hq.yml up -d --build
```

## 4. Applying Database Schema
On a new PC, you must run migrations for **both** Plant and HQ databases to create the tables.

### Plant Database
Run this command from the project root:
```bash
docker exec plant-plant_backend-1 sh -c "export DATABASE_URL=\$PLANT_DB_URL && alembic upgrade head"
```

### HQ Database
Run this command to create the HQ-specific tables:
```bash
docker exec hq-hq_backend-1 sh -c "export DATABASE_URL=\$HQ_DB_URL && export MIGRATION_TARGET=hq && alembic upgrade head"
```

## 5. First-Time Access
1. **Plant UI**: [http://localhost:5173](http://localhost:5173)
2. **HQ Dashboard**: [http://localhost:8081](http://localhost:8081)
3. **Login**: Use the `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PIN` you set in step 2.

## 6. Verification
- Go to the **Assets** tab to verify the hierarchy system is working.
- Go to **Admin > Master Management** and verify **Dynamic Masters** and **Self-Learning** are visible.
- Generate a test report in the **Reports** tab.

---
**Note:** Always keep your `.env` files secure and never commit them to version control.
