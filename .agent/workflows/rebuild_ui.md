---
description: Force Rebuild Plant UI (Fixes dependency/cache issues)
---

# Rebuild Plant UI

Use this workflow when:
*   You have installed new npm packages.
*   Changes to `package.json` or `vite.config.js` are not reflecting.
*   The UI seems "stuck" on an old version despite file saves.

1.  Navigate to the project root.
    // turbo
    cd d:\Official\AssetIQ_Production_Batch-9

2.  Rebuild and restart only the UI container.
    // turbo
    docker-compose -p plant -f docker/plant/docker-compose.plant.yml up -d --build plant_ui

3.  Show logs to confirm startup.
    docker logs -f plant-plant_ui-1
