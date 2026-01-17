# 🐳 Docker & Docker Compose Cheatsheet

A comprehensive reference for general Docker and Docker Compose commands, with examples relevant to the AssetIQ project structure.

---

## 🏗️ Docker Compose (Multi-Container)
Commands are typically run from the directory containing `docker-compose.yml`.

| Action | Command | Description |
| :--- | :--- | :--- |
| **Start** | `docker compose up -d` | Start services in background (detached). |
| **Stop** | `docker compose stop` | Stop running containers (doesn't remove them). |
| **Down** | `docker compose down` | Stop and **remove** containers, networks, and images. |
| **Build** | `docker compose build` | Build or rebuild service images. |
| **Build & Run** | `docker compose up -d --build` | Force rebuild and restart services. |
| **Logs** | `docker compose logs -f` | Tail logs for all services in the compose file. |
| **Specific Logs** | `docker compose logs -f <service>` | Tail logs for a specific service (e.g., `plant_backend`). |
| **Pull** | `docker compose pull` | Pull the latest versions of images. |
| **Restart** | `docker compose restart` | Restart all services. |
| **Project Name** | `docker compose -p <name> ...` | Run commands using a specific project name. |
| **File Path** | `docker compose -f <path> ...` | Run commands using a specific file path. |

---

## � Docker Containers (Individual)

| Action | Command | Description |
| :--- | :--- | :--- |
| **List Running** | `docker ps` | List all currently running containers. |
| **List All** | `docker ps -a` | List all containers (including stopped ones). |
| **Status (Stats)** | `docker stats` | Live stream of container resource usage (CPU, Mem). |
| **Execute CMD** | `docker exec -it <id/name> bash` | Open an interactive terminal inside a container. |
| **Copy File TO** | `docker cp <file> <id>:/path` | Copy a file from host to container. |
| **Copy File FROM** | `docker cp <id>:/path <file>` | Copy a file from container to host. |
| **Inspect** | `docker inspect <id/name>` | Get detailed low-level info about a container. |
| **Rename** | `docker rename <old> <new>` | Rename an existing container. |

---

## �️ Docker Images

| Action | Command | Description |
| :--- | :--- | :--- |
| **List Images** | `docker images` | List all locally stored images. |
| **Build Image** | `docker build -t <tag> .` | Build an image from a Dockerfile in current dir. |
| **Remove Image** | `docker rmi <id/name>` | Delete a specific image. |
| **Remove All** | `docker image prune -a` | Remove all unused images. |
| **Tag Image** | `docker tag <old> <new>` | Create a new tag for an existing image. |

---

## 🌐 Networking & Volumes

| Action | Command | Description |
| :--- | :--- | :--- |
| **List Networks** | `docker network ls` | List all Docker networks. |
| **Create Network** | `docker network create <name>` | Create a new virtual network. |
| **List Volumes** | `docker volume ls` | List all persistent volumes. |
| **Remove Volume** | `docker volume rm <name>` | Delete a specific volume. |
| **Volume Prune** | `docker volume prune` | Delete all unused local volumes. |

---

## 🧹 Cleanup & Maintenance (Danger Zone)

| Action | Command | Description |
| :--- | :--- | :--- |
| **Prune All** | `docker system prune` | Remove stopped containers, unused networks/images. |
| **Deep Clean** | `docker system prune -a --volumes` | Remove **everything** not used by a running container. |
| **Disk Usage** | `docker system df` | Show how much space Docker is using. |

---

## 💡 Practical AssetIQ Examples

**Running with Custom Port:**
```powershell
# Using environment variables to override defaults
$env:PLANT_HTTP_PORT=9000; docker compose -f docker-compose.plant.yml up -d
```

**Checking why a container failed to start:**
```powershell
docker inspect --format='{{.State.Error}}' <container_name>
```

**Running a script inside the backend:**
```powershell
docker exec -it plant-plant_backend-1 python tools/some_script.py
```
