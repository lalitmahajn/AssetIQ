---
description: Start or Restart the HQ Environment (Backend, Worker, DB)
---

# Run HQ Environment

This workflow starts the HQ environment using Docker Compose.

1.  Navigate to the project root.
    // turbo
    cd d:\Official\AssetIQ

2.  Run Docker Compose for HQ.
    // turbo
    docker-compose -p hq -f docker/hq/docker-compose.hq.yml up -d

3.  Check the status of the containers.
    docker ps --filter "name=hq"

4.  HQ UI is ready at:
    // turbo
    Write-Host "HQ UI is ready: http://localhost:8100/hq/ui (or check your HQ_IP in .env)"
