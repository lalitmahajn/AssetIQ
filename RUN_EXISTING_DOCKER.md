# Running AssetIQ (Existing Setup)

Use this guide if you have **already built the images** previously and just want to start the application quickly without rebuilding.

## 1. Ensure Network Exists
The Plant and HQ nodes communicate over a shared Docker network. Ensure it is created:

```powershell
docker network create assetiq_net
```
*(If it already exists, Docker will just notify you, which is fine.)*

## 2. Start Plant Node
Start the Plant services (Backend, Frontend, DB) in the background:

```powershell
cd docker/plant
docker compose -f docker-compose.plant.yml up -d
```

## 3. Start HQ Node
Start the HQ services (Backend/Dashboard, DB) in the background:

```powershell
cd ../hq
docker compose -f docker-compose.hq.yml up -d
```

---

## Troubleshooting & Management

### Check Running Containers
To see all active containers and their status:
```powershell
docker ps
```

### Stop All Services
To stop the containers without removing the data:
```powershell
# Stop Plant
cd docker/plant
docker compose -f docker-compose.plant.yml stop

# Stop HQ
cd ../hq
docker compose -f docker-compose.hq.yml stop
```

### View Logs
If you need to debug a specific service (e.g., the Plant backend):
```powershell
docker logs -f plant-plant_backend-1
```
