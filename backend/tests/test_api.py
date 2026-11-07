from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.main import create_app
from app.db.session import create_database_engine, get_db
import app.main as main_module


def test_versioned_health_endpoint_returns_success_envelope() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"success": True, "data": {"status": "ok"}}


def test_readiness_endpoint_checks_sqlite_connectivity() -> None:
    test_engine = create_database_engine("sqlite://")
    test_sessions = sessionmaker(bind=test_engine)

    def override_get_db():
        with test_sessions() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/ready")
    finally:
        app.dependency_overrides.clear()
        test_engine.dispose()

    assert response.status_code == 200
    assert response.json() == {"success": True, "data": {"status": "ready"}}


def test_readiness_reports_database_unavailable_but_liveness_stays_up() -> None:
    class UnavailableSession:
        def execute(self, _statement):
            from sqlalchemy.exc import SQLAlchemyError

            raise SQLAlchemyError("database is unavailable")

        def close(self) -> None:
            pass

    app = create_app()
    app.dependency_overrides[get_db] = lambda: UnavailableSession()

    try:
        with TestClient(app) as client:
            live_response = client.get("/api/v1/health")
            ready_response = client.get("/api/v1/ready")
    finally:
        app.dependency_overrides.clear()

    assert live_response.status_code == 200
    assert ready_response.status_code == 503
    assert ready_response.json() == {
        "error": {
            "code": "database_unavailable",
            "message": "The database is unavailable.",
            "details": [],
        }
    }


def test_application_shutdown_disposes_sqlalchemy_engine(monkeypatch) -> None:
    disposed = []

    class EngineStub:
        def dispose(self) -> None:
            disposed.append(True)

    monkeypatch.setattr(main_module, "engine", EngineStub())

    with TestClient(create_app()):
        pass

    assert disposed == [True]


def test_cors_allows_existing_vite_development_origin() -> None:
    client = TestClient(create_app())

    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_http_errors_use_standard_error_envelope() -> None:
    app = create_app()

    @app.get("/api/v1/test-conflict")
    def conflict() -> None:
        raise HTTPException(status_code=409, detail="State conflict")

    response = TestClient(app).get("/api/v1/test-conflict")

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "conflict",
            "message": "State conflict",
            "details": [],
        }
    }


def test_request_validation_uses_standard_error_envelope() -> None:
    app = create_app()

    @app.get("/api/v1/test-validation")
    def validate_count(count: int) -> dict[str, int]:
        return {"count": count}

    response = TestClient(app).get("/api/v1/test-validation?count=not-an-integer")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["details"][0]["location"] == ["query", "count"]
