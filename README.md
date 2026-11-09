# CampusCycle

An Inter-College Resource Sharing and Redistribution Platform.

## Overview

CampusCycle connects colleges and educational institutions to facilitate sharing, exchanging, donating and redistributing surplus educational resources.

## Problem Statement

Educational institutions often have unused resources while other institutions face shortages. CampusCycle provides a centralized platform to discover, request, approve and transfer these resources.

## Core Features

- College Onboarding and Verification
- User Authentication (JWT + HTTP-only cookies with CSRF protection)
- Resource Marketplace and Multi-Filter Search
- Resource Listing Management & Image Uploads (JPEG, PNG, WebP)
- Request and Approval System (Donations, Exchanges, Purchase Enquiries)
- Real-time Inventory Management and Atomic Reservations
- Transfer & Shipment Tracking with Multi-Batch Deliveries
- Good/Damaged/Missing Item Receipt Inspections & Dispute Handling
- Interactive Analytics Dashboard with Platform and College Scopes

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite, Tailwind CSS v4, Lucide React, Axios |
| Web Server & Proxy | Nginx (Alpine) |
| Backend | Python 3.12, FastAPI, Uvicorn, Pydantic |
| ORM & Migrations | SQLAlchemy 2.0, Alembic |
| Database | SQLite with persistent named Docker volume storage |
| Containerization | Docker, Docker Compose |

---

## Docker Deployment (Phase 11)

CampusCycle is fully containerized and orchestrated with Docker Compose for production and local environments.

### Architecture

```text
Browser
   │
   ▼ (Port 5173 / HTTP)
┌────────────────────────────────────────────────────────┐
│  frontend container (nginx:1.27-alpine)                │
│  - Serves compiled React SPA assets                    │
│  - SPA fallback routing (try_files -> /index.html)     │
│  - Reverse-proxies /api/ requests to backend:8000      │
│  - Proxies /docs and /openapi.json to backend:8000     │
│  - Health endpoint at /healthz                         │
└───────────────────────────┬────────────────────────────┘
                            │ internal Docker network
                            ▼ (http://backend:8000)
┌────────────────────────────────────────────────────────┐
│  backend container (python:3.12-slim)                  │
│  - Runs FastAPI via Uvicorn (UID 10001 campuscycle)    │
│  - Automatic startup migration (alembic upgrade head)  │
│  - Health endpoint at /api/v1/health                   │
│  - Loopback host binding (127.0.0.1:8000)              │
└───────────────────────────┬────────────────────────────┘
                            │ mounted at /data
                            ▼
┌────────────────────────────────────────────────────────┐
│  named volume: campuscycle_data                        │
│  - /data/campuscycle.db (SQLite database)              │
│  - /data/uploads/resource-images (uploaded images)     │
└────────────────────────────────────────────────────────┘
```

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (Docker Desktop on Windows/macOS or Docker Engine on Linux)
- [Docker Compose](https://docs.docker.com/compose/) (v2.20+)

### Quickstart

1. **Clone the repository:**
   ```bash
   git clone https://github.com/coderx001905/CampusCycle.git
   cd CampusCycle
   ```

2. **Configure environment (optional):**
   ```bash
   cp .env.example .env
   ```
   *The default configuration works out-of-the-box for local testing.*

3. **Build and start all services:**
   ```bash
   docker compose up -d --build
   ```

4. **Verify container status:**
   ```bash
   docker compose ps
   ```
   Both `campuscycle-frontend-1` and `campuscycle-backend-1` will report `Up (healthy)`.

5. **Access the application:**
   - **Frontend Web UI:** [http://localhost:5173](http://localhost:5173)
   - **Interactive API Documentation:** [http://localhost:5173/docs](http://localhost:5173/docs)
   - **Backend Direct Loopback (Dev):** [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

---

### Service Ports & Endpoints

| Service | Container Port | Host Port | Description |
|---|---|---|---|
| `frontend` | `80` | `5173` | React web application and Nginx reverse proxy |
| `frontend` | `80` | `5173/healthz` | Nginx liveness probe |
| `backend` | `8000` | `127.0.0.1:8000` | Direct FastAPI loopback (development / debugging) |
| `backend` | `8000` | internal | Accessible to frontend via service name `http://backend:8000` |

---

### SQLite Database & Volume Persistence

CampusCycle stores its SQLite database and uploaded resource images in a named Docker volume (`campuscycle_data`).

- **Volume Mount Point:** `/data` inside the `backend` container.
- **Database File:** `/data/campuscycle.db`.
- **Uploaded Images:** `/data/uploads/resource-images/`.
- **Persistence Guarantee:** Data is fully retained across container restarts (`docker compose restart`), service recreations (`docker compose down && docker compose up -d`), and image rebuilds.
- **Migrations:** The backend entrypoint runs `alembic upgrade head` on startup before launching Uvicorn, guaranteeing schema consistency.

> **Caution:** Do NOT use `docker compose down -v` unless you intentionally wish to delete all persistent database and image storage.

---

### Common Operational Commands

```bash
# View running containers and health checks
docker compose ps

# View live container logs
docker compose logs -f

# View backend logs only
docker compose logs -f backend

# View frontend logs only
docker compose logs -f frontend

# Restart services without deleting data
docker compose restart

# Stop containers (preserves volume and database)
docker compose down

# Start containers after stopping
docker compose up -d

# Execute CLI commands inside the backend container (e.g. admin provisioning)
docker compose exec backend python -m app.cli provision-admin
docker compose exec backend python -m app.cli reset-admin-password
```

---

### Troubleshooting

- **Port 5173 already in use:**
  Set `CC_FRONTEND_PORT=8080` (or another free port) in `.env` and run `docker compose up -d`.
- **Health check timeout:**
  Check backend logs with `docker compose logs backend` to inspect database migration or startup notices.
- **Checking volume contents:**
  ```bash
  docker compose exec backend ls -la /data
  ```
