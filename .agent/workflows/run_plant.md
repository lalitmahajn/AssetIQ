---
description: Start or Restart the Plant Environment (Backend, UI, DB)
---

# Run Plant Environment

This workflow starts the Plant environment using Docker Compose.

1.  Navigate to the project root.
    // turbo
    cd d:\Official\AssetIQ_Production_Batch-9

2.  Run Docker Compose for Plant.
    // turbo
    docker-compose -p plant -f docker/plant/docker-compose.plant.yml up -d

3.  Check the status of the containers.
    docker ps --filter "name=plant"

4.  Plant UI is ready at:
    // turbo
    Write-Host "Plant UI is ready: http://localhost:5173 (or check your PLANT_IP in .env)"
