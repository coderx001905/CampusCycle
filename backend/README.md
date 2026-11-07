# CampusCycle Backend

The backend is a FastAPI application using SQLAlchemy 2.x, SQLite, and Alembic. It implements the approved seven-table persistence schema and Phase 5 authentication, college onboarding, account management, and authorization. Resource/request/transfer business workflows and frontend-backend integration remain later phases.

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

## Authentication and first Platform Admin

Install the updated requirements and apply the approved schema to the local development database before using authentication:

```powershell
Set-Location D:\CampusCycle\backend
..\.venv\Scripts\Activate.ps1
alembic upgrade head
python -m app.cli provision-admin
```

The command prompts for the administrator name and email, then prompts twice for a hidden password. It creates the only initial global `platform_admin` (`college_id` is null), hashes the password with Argon2id, and refuses another administrator after one exists. It does not seed credentials or expose an HTTP administrator-registration route. Do not place a real secret in shell arguments or logs.

Public registration uses `POST /api/v1/auth/register` with `college` and `representative` objects. The college and its first representative are created atomically; the college starts `pending`. Registration returns safe account details and does not automatically issue a session. The representative can sign in to browse, but pending/rejected college eligibility is unavailable to future transactional services until an administrator verifies the college.

Login returns a 15-minute HS256 access JWT in the JSON response and places the 7-day refresh JWT only in an HttpOnly cookie. The refresh JWT is signed, carries a unique `jti` and token-family ID, and only its SHA-256 digest is stored in `refresh_tokens`. Refresh rotates the token and links the records. Reuse of a rotated token revokes its family. Logout revokes the presented refresh token; issued access JWTs remain valid until expiry.

### Browser CSRF flow and cookies

Refresh and logout require both an allowed `Origin` and signed double-submit CSRF protection. The backend issues a random nonce and signs `expiry.nonce.SHA256(refresh-cookie)` with the dedicated `CC_CSRF_SECRET_KEY` using HMAC-SHA256. The signed value is set in the JavaScript-readable CSRF cookie at `CC_CSRF_COOKIE_PATH=/` so frontend pages can read it. The browser copies that exact value to `X-CSRF-Token`; the backend uses constant-time equality checks, verifies the HMAC and expiry, and verifies that the signature is bound to the presented refresh cookie. Refresh rotates both cookies. Logout clears both with their configured paths. The HttpOnly refresh cookie stays scoped to `CC_AUTH_COOKIE_PATH=/api/v1/auth`.

For local development, use the same hostname for the frontend and backend. The existing Vite origin `http://localhost:5173` is allowed; use `http://localhost:8000` for direct backend requests. `localhost` and `127.0.0.1` have separate cookie scopes even though both are allowed CORS origins. CORS credentials are enabled only for explicit origins; wildcard origins are rejected by settings validation.

Production must use HTTPS (`CC_COOKIE_SECURE=true`). Select `CC_COOKIE_SAMESITE=lax` when frontend and API are same-site; use `none` only for a genuinely cross-site deployment, always with Secure and a deliberate CSRF/CORS review. Set `CC_COOKIE_DOMAIN` only when both applications share a registrable parent domain and cookie sharing is required; prefer a host-only cookie otherwise. Keep `CC_AUTH_COOKIE_PATH=/api/v1/auth` so refresh/logout receive the refresh cookie. Set strong, independent random values of at least 32 characters for `CC_JWT_SECRET_KEY` and `CC_CSRF_SECRET_KEY`. Example placeholders are development-only and production settings reject them.

### Implemented Phase 5 endpoints

- `POST /api/v1/auth/register`, `/login`, `/refresh`, `/logout`; `GET /api/v1/auth/me`
- `GET/PATCH /api/v1/colleges/me`; `GET /api/v1/colleges`; `GET /api/v1/colleges/{college_id}`
- `PATCH /api/v1/admin/colleges/{college_id}/verification`
- `GET/PATCH /api/v1/users/me`; `GET/POST /api/v1/colleges/me/users`
- `PATCH /api/v1/users/{user_id}/status`

Profile update schemas accept only a user's name/email and a college's name/address/city/contact email. They reject role, college ownership, active state, verification status, and password-hash fields. Password changes are not part of the approved Phase 5 endpoint contract. College representatives can access only their own college and its representative accounts; Platform Admin has the approved global college/account management scope. College status changes are recorded through the existing `updated_at` field and application log; no history table was added because none is approved.

The approved schema does not specify which individual college profile fields are editable. The implementation limits updates to the existing college identity/contact columns and excludes verification/ownership fields. Public registration does not auto-login because the API contract does not define an issued-session response; login is a separate step.

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

The database layer does not implement resource/request/transfer service rules. College ownership checks for those business records, atomic inventory reservations, transfer state transitions, aggregate transfer quantities, and cancellation/dispute permissions remain for their designated later phases. Phase 5 implements refresh-token rotation and reuse detection using the approved seven-day lifetime. Purchase payments remain outside CampusCycle. Optional refresh-token user-agent and IP columns are left NULL because the project has not approved a collection or retention policy for those values.

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
