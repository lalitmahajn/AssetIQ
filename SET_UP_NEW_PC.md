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
3. Add HQ Dashboard credentials:
```env
HQ_BOOTSTRAP_ADMIN_USERNAME=admin
HQ_BOOTSTRAP_ADMIN_PIN=142536
```

## 3. Launching the Services

Before starting the containers, you **must** create the shared Docker network:
```bash
docker network create assetiq_net
```

Open a terminal in the project root and run:

### 1. Start Plant Services
```bash
docker-compose -f docker/plant/docker-compose.plant.yml up -d --build
```

### 2. Initialize Database (CRITICAL)
You must apply the database migrations manually to create the tables:
```bash
docker-compose -f docker/plant/docker-compose.plant.yml exec -e MIGRATION_TARGET=plant plant_backend alembic upgrade head
```
> **Note**: Without this step, the application will crash because the database tables won't exist.

### Start HQ
```bash
docker-compose -f docker/hq/docker-compose.hq.yml up -d --build
```

## 4. Windows Firewall Configuration (Critical for Live Access)
To access the UI and API from other devices on the same network, you must allow traffic through the Windows Firewall. Run this in **PowerShell as Administrator**:

```powershell
# Plant Ports
New-NetFirewallRule -DisplayName "AssetIQ Plant UI" -Direction Inbound -LocalPort 5173 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "AssetIQ Plant API" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow

# HQ Ports
New-NetFirewallRule -DisplayName "AssetIQ HQ Dashboard" -Direction Inbound -LocalPort 8100 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "AssetIQ HQ Proxy" -Direction Inbound -LocalPort 8081 -Protocol TCP -Action Allow
```

## 5. First-Time Access
1. **Plant UI**: [http://localhost:5173](http://localhost:5173)
   - **Login**: Use the `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PIN` set in `docker/plant/.env`.
2. **HQ Dashboard**: [http://localhost:8081/hq/ui](http://localhost:8081/hq/ui)
   - **Login**: Use the `HQ_BOOTSTRAP_ADMIN_USERNAME` and `HQ_BOOTSTRAP_ADMIN_PIN` set in `docker/hq/.env`.

## 6. Verification
- Go to the **Assets** tab to verify the hierarchy system is working.
- Go to **Admin > Master Management** and verify **Dynamic Masters** and **Self-Learning** are visible.
- Generate a test report in the **Reports** tab.

---
**Note:** Always keep your `.env` files secure and never commit them to version control.
