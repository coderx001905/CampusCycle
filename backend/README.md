# CampusCycle Backend

The backend is a FastAPI application using SQLAlchemy 2.x, SQLite, and Alembic. It implements the approved seven-table persistence schema, Phase 5 authentication and college/user management, Phase 6 resource listings and local resource images, and Phase 7 request approvals and inventory reservations. Transfers, analytics, and frontend-backend integration remain later phases.

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

## Phase 7 request and reservation workflows

Request endpoints use the `/api/v1` prefix and return the established success/error envelopes. Only verified college representatives may transact; request identity comes from the authenticated account, and request details are visible only to the requesting college and the college owning the requested resource.

| Method and path | Purpose |
|---|---|
| `POST /requests` | Submit a donation, exchange, or purchase enquiry without reserving stock. |
| `GET /requests/mine` | Paginated requests submitted by the caller's college. |
| `GET /requests/received` | Paginated requests for resources owned by the caller's college. |
| `GET /requests/{request_id}` | Retrieve a request as one of its participating colleges. |
| `POST /requests/{request_id}/approve` | Approve a pending request; donation approval can be partial, while exchange and purchase enquiries require full approval. |
| `POST /requests/{request_id}/reject` | Reject a pending request with a required reason. |
| `POST /requests/{request_id}/purchase-confirmation` | Confirm an approved purchase enquiry and reserve its approved quantity. |
| `POST /requests/{request_id}/cancel` | Submit a request-level cancellation before transfer rows exist. |
| `POST /requests/{request_id}/cancellation-decision` | Resource-owning college approves or rejects a cancellation. |

SQLite write operations acquire `BEGIN IMMEDIATE`; inventory uses conditional updates and row-count checks. Exchange approval reserves both resources in one transaction. Purchase approval does not reserve stock; confirmation reserves it, or persists `awaiting_resolution` and confirmation metadata before returning HTTP 409 `insufficient_stock`. Request cancellation is recorded on the request row; it releases only that request's reservation after approval and before any transfer exists. Rejection and cancellation reasons are stored on the existing `requests` table. Phase 7 migration `a73c5f91d2e4` adds these request fields and constraints without adding a business table, and corrective migration `2d1946b08dd1` updates the `ck_requests_approved_quantity` check constraint to enforce at the database level that `approved_quantity` may be partial for donations, but must equal `requested_quantity` for exchange and purchase enquiries when non-null. Tests use isolated temporary SQLite databases; no migration was applied to the persistent local database.

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

The database layer supplies persistence and constraints; service-layer resource ownership, listing visibility, status rules, and inventory reads are implemented in Phase 6. Request workflows and atomic inventory reservations, transfer state transitions, aggregate transfer quantities, and cancellation/dispute permissions remain for their designated later phases. Phase 5 implements refresh-token rotation and reuse detection using the approved seven-day lifetime. Purchase payments remain outside CampusCycle. Optional refresh-token user-agent and IP columns are left NULL because the project has not approved a collection or retention policy for those values.

## Phase 6 resource management

All resource endpoints use the `/api/v1` prefix and the approved `{"success": true, "data": ...}` response envelope.

| Method and path | Access | Purpose |
|---|---|---|
| `POST /resources` | Verified College Representative | Create a listing; college/creator identity and initial inventory are server-derived. |
| `GET /resources` | Any authenticated user | Browse active, stocked listings with search, filters, and pagination. |
| `GET /resources/{resource_id}` | Any authenticated user | Read an active listing; an owner may also view their inactive/depleted listing. |
| `PATCH /resources/{resource_id}` | Owning College Representative | Edit descriptive fields only. |
| `PATCH /resources/{resource_id}/status` | Owning College Representative | Activate or deactivate a listing. `depleted` is system-managed. |
| `GET /inventory/me` | Verified College Representative | Read all own-college listing quantities, including reserved quantity. |
| `POST /resources/{resource_id}/image` | Owning College Representative | Upload a listing image as multipart field `file`. |
| `GET /resources/{resource_id}/image` | Authenticated user with listing visibility | Serve a validated image through the API. |
| `DELETE /resources/{resource_id}/image` | Owning College Representative | Remove the listing image. |

Example listing creation request:

```json
{
  "name": "Calculus Textbook",
  "description": "First year mathematics textbook",
  "category": "Books",
  "condition": "Good, lightly used",
  "quantity": 8,
  "unit": "copies",
  "transfer_type": "donation",
  "indicative_price": null
}
```

The endpoint initializes `quantity_total` and `quantity_available` from `quantity`, sets `quantity_reserved` to zero, and sets status to `active`. The response exposes available quantity but not total or reserved quantities. `GET /resources` accepts `search`, `category`, `condition`, `transfer_type`, `college_id`, `page` (default 1), and `page_size` (default 20, maximum 100). Search covers name and description; category and condition use case-insensitive exact matching. Marketplace responses include pagination metadata and only active listings with positive physical stock. Owner inventory is a separate response and is restricted to the verified caller's college.

Example creation response:

```json
{
  "success": true,
  "data": {
    "id": 42,
    "name": "Calculus Textbook",
    "description": "First year mathematics textbook",
    "category": "Books",
    "condition": "Good, lightly used",
    "quantity_available": 8,
    "unit": "copies",
    "transfer_type": "donation",
    "indicative_price": null,
    "status": "active",
    "image_url": null,
    "college": {"id": 4, "name": "North College", "city": "Pune"}
  }
}
```

Resource edits accept only `name`, `description`, `category`, `condition`, `unit`, `transfer_type`, and `indicative_price`. Quantity and status cannot be edited through that endpoint. Representatives can set `active` or `inactive`; the service marks a resource `depleted` when physical `quantity_total` is zero. Zero available quantity alone does not deplete a listing. Reactivation requires positive physical stock. Reservation and stock-adjustment workflows remain outside Phase 6.

Images must be JPEG, PNG, or WebP, no larger than 5 MiB, and the filename extension, MIME type, and decoded file format must agree. The request-receiving middleware counts actual streamed bytes for this upload route before FastAPI parses multipart data, with a 64 KiB allowance for multipart framing and headers. It does not buffer the body and does not rely on `Content-Length`; over-limit requests receive the standard 413 error envelope. Pillow checks dimensions before full decoding and rejects images above 12 million pixels or 6,000 pixels on either side, verifies and decodes accepted images, rejects animation, applies orientation, then re-encodes to strip supplied metadata. The server generates a UUID filename and stores only that generated reference in `resources.image_path`; client filenames and paths are never used as storage paths. The directory defaults to `backend/uploads/resource-images` and can be changed with `CC_RESOURCE_IMAGE_DIR` (absolute paths are also supported). The default upload directory is excluded from Git. Replacement and removal use a conditional database update against the previously observed image reference; stale concurrent operations receive 409 and cannot overwrite a newer image. Replacement writes the new file before committing its reference and removes the previous file only after commit. Failed database writes clean up the new file and preserve the old reference/file. Storage-directory creation errors are reported without masking the original failure.

Phase 6 tests use isolated temporary SQLite databases and temporary image directories. Run the full backend suite from `D:\CampusCycle\backend`:

```powershell
..\.venv\Scripts\python.exe -m pytest -q
```

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
