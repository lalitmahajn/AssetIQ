# AssetIQ - Quick Start & Running Guide

This guide provides developer-focused instructions for getting the AssetIQ project (Plant Node + HQ Node) up and running quickly.

For detailed production deployment steps, see [README_RUNBOOK.md](README_RUNBOOK.md).

## 1. Prerequisites

- **Docker Desktop** (or Docker Engine + Docker Compose)
- **Git**

## 2. Initial Setup (Crucial)

### A. Create Docker Network
The project uses an external docker network named `assetiq_net` to allow containers to communicate across separate compose files. You **must** create this manually once.

```bash
docker network create assetiq_net
```

### B. Environment Variables (.env)
Docker Compose expects the `.env` file to be inside the specific docker folder you are running.

1.  **Plant Node**: Copy `.env.example` (if available) or create a new `.env` file inside `docker/plant/`.
2.  **HQ Node**: Create a `.env` file inside `docker/hq/`.

**Minimal Plant `.env` content (`docker/plant/.env`):**
```ini
# Secrets (Must be 32+ chars)
JWT_SECRET=dev_secret_0000000000000000000000000000
SYNC_HMAC_SECRET=dev_secret_0000000000000000000000000000
STATION_SECRET_ENC_KEY=dev_secret_0000000000000000000000000000

# Database
PLANT_POSTGRES_PASSWORD=postgres
APP_ENV=dev

# First Run Bootstrap (Creates the admin user)
BOOTSTRAP_ADMIN_EMAIL=admin@example.com
BOOTSTRAP_ADMIN_PIN=123456
```

## 3. Running the Plant Node

The Plant Node consists of the Backend, Worker, Database, and UI.

### Start Services
1.  Navigate to the plant docker directory:
    ```bash
    cd docker/plant
    ```
2.  Run Docker Compose:
    ```bash
    docker compose -f docker-compose.plant.yml up -d --build
    ```

### Accessing the Application
- **Web UI**: [http://localhost:5173](http://localhost:5173)
- **API (Production)**: [http://localhost:8080](http://localhost:8080) *(via Nginx)*
- **API (Dev)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8080/healthz](http://localhost:8080/healthz)

### First Login
Use the credentials you defined in `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PIN` (API Login) or via the UI if implemented.

---

## 4. Running the HQ Node (Optional)

The HQ Node aggregates data from Plant Nodes.

### Start Services
1.  Navigate to the HQ docker directory:
    ```bash
    cd docker/hq
    ```
    *(Ensure you have a `.env` file here too!)*
2.  Run Docker Compose:
    ```bash
    docker compose -f docker-compose.hq.yml up -d --build
    ```

### Accessing HQ
- **Web UI**: [http://localhost:8081/hq/ui](http://localhost:8081/hq/ui)
- **API (Production)**: [http://localhost:8081](http://localhost:8081) *(via Nginx)*
- **API (Dev)**: [http://localhost:8100/docs](http://localhost:8100/docs)

---

## 5. Troubleshooting

### Issue: "Network assetiq_net declared as external, but could not be found"
**Cause**: You skipped the network creation step.
**Fix**:
```bash
docker network create assetiq_net
```

### Issue: Containers exit immediately / "Missing secret" errors
**Cause**: Docker Compose cannot find the `.env` file.
**Fix**: Ensure your `.env` file is exactly inside `docker/plant/` (for plant) or `docker/hq/` (for hq). DO NOT put it in the root directory.

### Issue: "PIN is too weak" during bootstrap
**Cause**: The `BOOTSTRAP_ADMIN_PIN` is too simple (e.g., 0000, 1111).
**Fix**: Change the PIN in your `.env` to something more complex (e.g., `852096`) and restart:
```bash
docker compose -f docker-compose.plant.yml up -d
```

### Issue: Port Conflicts
**Cause**: Ports `8000`, `5173`, `5432` might be in use.
**Fix**: Change the ports in your `.env` file:
```ini
PLANT_HTTP_PORT=8005
PLANT_UI_PORT=5174
PLANT_POSTGRES_PORT=5435
```
