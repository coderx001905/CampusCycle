# CampusCycle Backend

FastAPI backend foundation for CampusCycle Phase 3. It provides the API application, configuration, health/readiness checks, SQLAlchemy session infrastructure, security primitives, standardized errors, and logging. Business models, migrations, and authentication endpoints are later-phase work.

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
