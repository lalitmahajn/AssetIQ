# ==========================================
# ASSETIQ DEVELOPMENT COMMAND CENTER
# ==========================================
# How to use: Uncomment the section you need and run the script.
# Tip: Use CTRL+/ to toggle comments in VS Code.

Write-Host "Starting AssetIQ Dev Script..." -ForegroundColor Cyan

# ------------------------------------------
# 0. PREREQUISITES (Run once)
# ------------------------------------------
# Create the shared network if it doesn't exist
# docker network create assetiq_net


# ------------------------------------------
# 1. PLANT ENVIRONMENT (Standard Start)
# ------------------------------------------
# Starts existing containers. Fast start.
# Write-Host "Starting Plant..." -ForegroundColor Green
# docker-compose -p plant -f docker/plant/docker-compose.plant.yml up -d


# ------------------------------------------
# 2. PLANT ENVIRONMENT (Rebuild)
# ------------------------------------------
# Use this when you changed code (Python/JS) or Dockerfiles.
# Write-Host "Rebuilding and Starting Plant..." -ForegroundColor Yellow
# docker-compose -p plant -f docker/plant/docker-compose.plant.yml up -d --build


# ------------------------------------------
# 3. PLANT UI ONLY (Fast Rebuild)
# ------------------------------------------
# Use when only frontend code changed.
# Write-Host "Rebuilding Plant UI..." -ForegroundColor Yellow
# docker-compose -p plant -f docker/plant/docker-compose.plant.yml up -d --build plant_ui


# ------------------------------------------
# 4. HQ ENVIRONMENT (Standard Start)
# ------------------------------------------
# Write-Host "Starting HQ..." -ForegroundColor Green
# docker-compose -p hq -f docker/hq/docker-compose.hq.yml up -d


# ------------------------------------------
# 5. HQ ENVIRONMENT (Rebuild)
# ------------------------------------------
# Write-Host "Rebuilding HQ..." -ForegroundColor Yellow
# docker-compose -p hq -f docker/hq/docker-compose.hq.yml up -d --build


# ------------------------------------------
# 6. LOGS (Follow Output)
# ------------------------------------------
# View backend logs (Ctrl+C to exit)
# docker-compose -p plant -f docker/plant/docker-compose.plant.yml logs -f plant_backend
# docker-compose -p hq -f docker/hq/docker-compose.hq.yml logs -f hq_backend


# ------------------------------------------
# 7. DATABASE UTILS
# ------------------------------------------
# Check Plant tables
# docker exec plant-postgres-1 psql -U assetiq -d assetiq_plant -c "\dt"

# Check HQ tables
# docker exec hq-hq_postgres-1 psql -U assetiq -d assetiq_hq -c "\dt"

Write-Host "Done!" -ForegroundColor Cyan
