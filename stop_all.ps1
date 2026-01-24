# ==========================================
# ASSETIQ CLEANUP & SHUTDOWN UTILITY
# ==========================================
# Use this script to stop services or completely reset the environment.
# Uncomment the section you need.

Write-Host "Starting AssetIQ Cleanup..." -ForegroundColor Cyan

# ------------------------------------------
# 1. STANDARD STOP (Safe Shutdown)
# ------------------------------------------
# Stops containers but PRESERVES database data.
# Write-Host "Stopping all services..." -ForegroundColor Yellow
# docker-compose -p plant -f docker/plant/docker-compose.plant.yml down
# docker-compose -p hq -f docker/hq/docker-compose.hq.yml down


# ------------------------------------------
# 2. NUCLEAR OPTION (Fresh Install Simulation)
# ------------------------------------------
# ⚠️ WARNING: THIS DELETES ALL DATABASE DATA! ⚠️
# Resets the environment to zero (like a new PC).
# Write-Host "DESTROYING PLANT DATA..." -ForegroundColor Red
# docker-compose -p plant -f docker/plant/docker-compose.plant.yml down -v

# Write-Host "DESTROYING HQ DATA..." -ForegroundColor Red
# docker-compose -p hq -f docker/hq/docker-compose.hq.yml down -v


# ------------------------------------------
# 3. CLEANUP EVERYTHING (Prune)
# ------------------------------------------
# Removes unused networks, containers, and dangling images
# docker system prune -f

Write-Host "Cleanup Complete!" -ForegroundColor Cyan
