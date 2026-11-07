# CampusCycle Backend

The backend is a FastAPI application using SQLAlchemy 2.x, SQLite, and Alembic. Phase 4 adds the approved seven-table persistence schema. Authentication endpoints and business workflows remain later-phase work.

## Local development

From the repository root in PowerShell, activate the root Python 3.12 environment and install runtime and development dependencies:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt -r backend\requirements-dev.txt
Copy-Item backend\.env.example backend\.env
```

Start the API from `D:\CampusCycle\backend`:

```powershell
..\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

`GET /api/v1/health` is a liveness check. `GET /api/v1/ready` checks SQLite connectivity. Interactive API documentation is at `/docs`. Local SQLite defaults to `backend\campuscycle.db` when the API is started from the backend directory; database files are ignored by Git.

## Database schema

SQLAlchemy mappings live under `app/models/`. The approved schema contains exactly these seven business tables:

1. `colleges` — college identity, contact details, verification state, and timestamps.
2. `users` — Platform Admin and college representative accounts; case-insensitive unique email.
3. `resources` — college-owned listings, inventory balances, resource type, and indicative price.
4. `requests` — donation, exchange, and purchase enquiry records with review and purchase-intention information.
5. `transfers` — partial movement batches, receipt quantities, disputes, cancellation review, and replacement links.
6. `transfer_status_history` — user or system status audit entries.
7. `refresh_tokens` — hashed-token persistence, unique JTI and family identifiers, expiry, revocation, and rotation lineage.

Relationships use explicit foreign keys and `RESTRICT` deletion behavior for business records. Database constraints cover enumerated statuses/types, role/college combinations, positive request/transfer quantities, exchange offer fields, inventory balance, receipt totals, and unique token identifiers/hashes. The user email index uses SQLite `lower(email)`; its expression is not reflected by all Alembic/SQLAlchemy SQLite versions, so preserve the explicit index in migration revisions. Resource `condition` stays a flexible string because the approved design does not finalize its values.

Date/time values use the `UTCDateTime` SQLAlchemy type: values are normalized to UTC on writes and returned timezone-aware on reads. Created/updated timestamps use UTC defaults, with `updated_at` refreshed on ORM updates.

The database layer does not implement service-level business rules. College ownership checks, atomic inventory reservations, transfer state transitions, aggregate transfer quantities, cancellation/dispute permissions, and refresh-token rotation/reuse detection remain for their designated later phases. Refresh token issuance must use the approved seven-day lifetime; no refresh endpoint or operational token workflow is included here. Purchase payments remain outside CampusCycle.

## Alembic migrations

Alembic is the authoritative schema creation/evolution mechanism. FastAPI startup does not call `create_all()`. The initial revision creates the approved schema; the follow-up removes inferred status defaults so the database does not impose defaults absent from the approved specification.

From `D:\CampusCycle\backend`:

```powershell
..\.venv\Scripts\Activate.ps1
alembic upgrade head
alembic current
alembic revision --autogenerate -m "describe schema change"
```

Alembic reads `CC_DATABASE_URL` through the existing settings system and imports the application's SQLAlchemy metadata. SQLite foreign-key enforcement is enabled on migration and application connections. Review every generated revision before applying it; use isolated temporary databases for migration tests. Do not reset or drop the persistent development database.

## Tests

Run from `D:\CampusCycle\backend`:

```powershell
..\.venv\Scripts\Activate.ps1
python -m pytest
```

Database tests use temporary SQLite databases and cover model metadata, relationships, constraints, indexes, foreign keys, restricted deletion, UTC timestamps, and Alembic upgrade from an empty database.

## Docker development database

The root `compose.yaml` starts the backend only and keeps the existing `campuscycle_data` named volume mounted at `/data`; SQLite is stored at `/data/campuscycle.db`. The container runs as UID/GID 10001. From the repository root:

```powershell
docker compose build backend
docker compose up -d backend
docker compose exec backend alembic upgrade head
docker compose exec backend alembic current
```

Apply migrations intentionally with the command above; startup does not migrate automatically. The migration version and database tables persist in the named volume across container restarts. The frontend remains independently served by Vite. Full application deployment remains Phase 11.
