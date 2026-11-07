from datetime import datetime, timedelta, timezone

import jwt
import pytest
from pydantic import ValidationError
from sqlalchemy import text

from app.core.config import Settings
from app.core.security import create_access_token, decode_access_token
from app.db import session as database_session
from app.db.session import create_database_engine


def test_settings_can_be_loaded_without_an_env_file() -> None:
    settings = Settings(_env_file=None, app_name="Test CampusCycle API")

    assert settings.app_name == "Test CampusCycle API"
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.access_token_expire_minutes == 15


def test_development_jwt_fallback_is_rejected_outside_development() -> None:
    with pytest.raises(ValueError, match="only be used in development"):
        Settings(
            _env_file=None,
            environment="production",
            jwt_secret_key="local-compose-development-only-change-me",
        )


def test_settings_reject_non_hs256_jwt_algorithm() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, jwt_algorithm="HS384")


def test_sqlite_engine_connects_and_enforces_foreign_keys() -> None:
    engine = create_database_engine("sqlite://")

    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
    finally:
        engine.dispose()


def test_request_session_is_closed_after_dependency_finishes(monkeypatch: pytest.MonkeyPatch) -> None:
    class StubSession:
        closed = False

        def close(self) -> None:
            self.closed = True

        def rollback(self) -> None:
            pass

    stub = StubSession()
    monkeypatch.setattr(database_session, "SessionLocal", lambda: stub)
    dependency = database_session.get_db()

    assert next(dependency) is stub
    with pytest.raises(StopIteration):
        next(dependency)
    assert stub.closed


def test_access_token_round_trips_with_approved_identity_claims() -> None:
    settings = Settings(
        _env_file=None,
        jwt_secret_key="test-secret-long-enough-for-tests",
        jwt_issuer="test-campuscycle-api",
        jwt_audience="test-campuscycle-client",
    )

    token = create_access_token(
        subject="42",
        role="college_representative",
        college_id=8,
        settings=settings,
    )
    claims = decode_access_token(token, settings)

    assert claims["sub"] == "42"
    assert claims["role"] == "college_representative"
    assert claims["college_id"] == 8
    assert "exp" in claims
    assert claims["iss"] == settings.jwt_issuer
    assert claims["aud"] == settings.jwt_audience
    assert claims["exp"] - claims["iat"] == 15 * 60


def _signed_access_token(settings: Settings, *, issuer: str, audience: str, algorithm: str = "HS256") -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": "42",
        "iat": now,
        "exp": now + timedelta(minutes=15),
        "iss": issuer,
        "aud": audience,
    }
    return jwt.encode(claims, settings.jwt_secret_key, algorithm=algorithm)


def test_access_token_rejects_non_hs256_header_algorithm() -> None:
    settings = Settings(
        _env_file=None,
        jwt_secret_key="test-secret-long-enough-for-tests-with-extra-bytes-0123456789",
    )
    token = _signed_access_token(
        settings,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        algorithm="HS384",
    )

    with pytest.raises(jwt.InvalidAlgorithmError):
        decode_access_token(token, settings)


def test_access_token_rejects_invalid_issuer() -> None:
    settings = Settings(_env_file=None, jwt_secret_key="test-secret-long-enough-for-tests")
    token = _signed_access_token(
        settings,
        issuer="unexpected-issuer",
        audience=settings.jwt_audience,
    )

    with pytest.raises(jwt.InvalidIssuerError):
        decode_access_token(token, settings)


def test_access_token_rejects_invalid_audience() -> None:
    settings = Settings(_env_file=None, jwt_secret_key="test-secret-long-enough-for-tests")
    token = _signed_access_token(
        settings,
        issuer=settings.jwt_issuer,
        audience="unexpected-audience",
    )

    with pytest.raises(jwt.InvalidAudienceError):
        decode_access_token(token, settings)
