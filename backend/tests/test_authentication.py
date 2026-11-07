from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings, get_settings
from app.core.csrf import issue_csrf_token, verify_csrf_token
from app.core.security import decode_access_token
from app.core.passwords import hash_password, verify_password
from app.db.session import create_database_engine, get_db
from app.main import create_app
from app.models import Base, College, RefreshToken, User
from app.services.auth import provision_platform_admin
from app.services.auth import issue_refresh_token, rotate_refresh_token


@pytest.fixture
def auth_app(tmp_path):
    engine = create_database_engine(f"sqlite:///{(tmp_path / 'phase5.sqlite3').as_posix()}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    settings = Settings(
        _env_file=None,
        jwt_secret_key="phase-five-test-jwt-secret-with-enough-entropy",
        csrf_secret_key="phase-five-test-csrf-secret-with-enough-entropy",
        cors_origins=["http://localhost:5173"],
    )

    def override_db():
        session = sessions()
        try:
            yield session
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        yield app, sessions, settings
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def seed_rep(sessions, *, email="rep@example.edu", college_name="North College", status="verified"):
    with sessions.begin() as db:
        college = College(name=college_name, address="1 Road", city="Test City",
                          contact_email=f"{college_name.lower().replace(' ', '.')}@example.edu",
                          verification_status=status)
        user = User(name="Representative", email=email, password_hash=hash_password("GoodPassword!123"),
                    role="college_representative", college=college, is_active=True)
        db.add_all([college, user])
        db.flush()
        return user.id, college.id


def csrf_headers(client: TestClient, settings: Settings, refresh_cookie: str | None = None,
                 csrf_cookie: str | None = None) -> dict[str, str]:
    refresh_cookie = refresh_cookie or client.cookies.get(settings.refresh_cookie_name)
    csrf_cookie = csrf_cookie or client.cookies.get(settings.csrf_cookie_name)
    return {
        "Origin": "http://localhost:5173",
        "X-CSRF-Token": csrf_cookie,
        "Cookie": f"{settings.refresh_cookie_name}={refresh_cookie}; {settings.csrf_cookie_name}={csrf_cookie}",
    }


def test_password_hash_uses_argon_and_verifies_only_correct_password():
    encoded = hash_password("CorrectHorseBattery!234")
    assert encoded != "CorrectHorseBattery!234"
    assert encoded.startswith("$argon2")
    assert verify_password("CorrectHorseBattery!234", encoded)
    assert not verify_password("wrong-password", encoded)


def test_signed_csrf_token_is_bound_to_refresh_token_and_expires():
    token = issue_csrf_token(secret="dedicated-csrf-secret", refresh_token="refresh-one", lifetime_seconds=60)
    assert verify_csrf_token(token=token, secret="dedicated-csrf-secret", refresh_token="refresh-one")
    assert not verify_csrf_token(token=token, secret="wrong-secret", refresh_token="refresh-one")
    assert not verify_csrf_token(token=token, secret="dedicated-csrf-secret", refresh_token="refresh-two")
    expired = issue_csrf_token(secret="dedicated-csrf-secret", refresh_token="refresh-one", lifetime_seconds=-1)
    assert not verify_csrf_token(token=expired, secret="dedicated-csrf-secret", refresh_token="refresh-one")


def test_registration_is_atomic_pending_and_returns_no_password_data(auth_app):
    app, sessions, _settings = auth_app
    payload = {
        "college": {"name": "East College", "address": "42 Campus Road", "city": "Pune",
                    "contact_email": "office@east.edu"},
        "representative": {"name": "A. Representative", "email": "rep@east.edu",
                            "password": "ValidPassword!234"},
    }
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()["data"]
    assert body["college"]["verification_status"] == "pending"
    assert body["user"]["college_id"] == body["college"]["id"]
    assert "password" not in response.text and "password_hash" not in response.text
    with sessions() as db:
        college = db.get(College, body["college"]["id"])
        user = db.get(User, body["user"]["id"])
        assert college.verification_status == "pending"
        assert user.role == "college_representative"
        assert user.password_hash != payload["representative"]["password"]
        assert verify_password(payload["representative"]["password"], user.password_hash)


def test_registration_rejects_duplicate_email_and_injected_role_or_college(auth_app):
    app, sessions, _settings = auth_app
    seed_rep(sessions)
    with TestClient(app) as client:
        duplicate = client.post("/api/v1/auth/register", json={
            "college": {"name": "Other College", "address": "Road", "city": "Pune", "contact_email": "other@example.edu"},
            "representative": {"name": "Other Rep", "email": "REP@example.edu", "password": "ValidPassword!234"},
        })
        injected = client.post("/api/v1/auth/register", json={
            "college": {"name": "Other College", "address": "Road", "city": "Pune", "contact_email": "other@example.edu", "verification_status": "verified"},
            "representative": {"name": "Other Rep", "email": "new@example.edu", "password": "ValidPassword!234", "role": "platform_admin", "college_id": 999},
        })
    assert duplicate.status_code == 409
    assert injected.status_code == 422
    with sessions() as db:
        assert db.scalar(select(College).where(College.name == "Other College")) is None


def test_login_access_auth_and_refresh_cookie_rotation(auth_app):
    app, sessions, settings = auth_app
    user_id, college_id = seed_rep(sessions)
    with TestClient(app) as client:
        login = client.post("/api/v1/auth/login", json={"email": "REP@example.edu", "password": "GoodPassword!123"})
        assert login.status_code == 200, login.text
        assert login.json()["data"]["expires_in"] == 900
        assert login.json()["data"]["user"]["college_id"] == college_id
        assert settings.refresh_cookie_name in login.cookies
        assert login.cookies.get(settings.csrf_cookie_name)
        set_cookies = login.headers.get_list("set-cookie")
        refresh_set_cookie = next(value for value in set_cookies if value.startswith(settings.refresh_cookie_name + "="))
        csrf_set_cookie = next(value for value in set_cookies if value.startswith(settings.csrf_cookie_name + "="))
        assert "HttpOnly" in refresh_set_cookie and "HttpOnly" not in csrf_set_cookie
        assert "Path=/api/v1/auth" in refresh_set_cookie and "SameSite=lax" in refresh_set_cookie
        assert "Path=/;" in csrf_set_cookie
        assert "Secure" not in refresh_set_cookie  # local development default
        refresh_token = client.cookies.get(settings.refresh_cookie_name)
        csrf_token = client.cookies.get(settings.csrf_cookie_name)
        access = login.json()["data"]["access_token"]
        assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"}).status_code == 200
        claims = jwt.decode(access, settings.jwt_secret_key, algorithms=["HS256"], audience=settings.jwt_audience, issuer=settings.jwt_issuer)
        assert claims["sub"] == str(user_id) and claims["token_type"] == "access"
        rotated = client.post("/api/v1/auth/refresh", headers=csrf_headers(client, settings))
        assert rotated.status_code == 200, rotated.text
        replacement = client.cookies.get(settings.refresh_cookie_name)
        assert replacement != refresh_token
        assert client.cookies.get(settings.csrf_cookie_name) != csrf_token
    with sessions() as db:
        rows = db.scalars(select(RefreshToken).order_by(RefreshToken.id)).all()
        assert len(rows) == 2
        assert rows[0].token_hash != refresh_token
        assert rows[0].revoked_at is not None
        assert rows[0].replaced_by_token_id == rows[1].id
        assert rows[1].revoked_at is None


def test_refresh_reuse_revokes_entire_token_family(auth_app):
    app, sessions, settings = auth_app
    seed_rep(sessions)
    with TestClient(app) as client:
        client.post("/api/v1/auth/login", json={"email": "rep@example.edu", "password": "GoodPassword!123"})
        old_refresh = client.cookies.get(settings.refresh_cookie_name)
        old_csrf = client.cookies.get(settings.csrf_cookie_name)
        assert client.post("/api/v1/auth/refresh", headers=csrf_headers(client, settings)).status_code == 200
        replay = client.post("/api/v1/auth/refresh", headers=csrf_headers(client, settings, old_refresh, old_csrf))
        assert replay.status_code == 401
        assert "reuse" in replay.json()["error"]["message"].lower()
    with sessions() as db:
        rows = db.scalars(select(RefreshToken)).all()
        assert len(rows) == 2
        assert all(row.revoked_at is not None for row in rows)


def test_expired_rotated_token_still_triggers_family_reuse_detection(auth_app):
    _app, sessions, settings = auth_app
    user_id, _ = seed_rep(sessions)
    with sessions() as db:
        user = db.get(User, user_id)
        raw, first = issue_refresh_token(db, user=user, settings=settings)
        first.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        replacement, second = issue_refresh_token(db, user=user, settings=settings, family_id=first.token_family_id)
        first.revoked_at = datetime.now(timezone.utc) - timedelta(seconds=2)
        first.replaced_by = second
        # Keep the signed token's exp old while its token row represents a rotated session.
        # Re-signing with an expired exp produces a valid signed but expired refresh token.
        old_claims = jwt.decode(raw, settings.jwt_secret_key, algorithms=["HS256"],
                                 audience=settings.jwt_audience, issuer=settings.jwt_issuer)
        old_claims["exp"] = datetime.now(timezone.utc) - timedelta(seconds=1)
        raw = jwt.encode(old_claims, settings.jwt_secret_key, algorithm="HS256")
        first.token_hash = hashlib.sha256(raw.encode()).hexdigest()
        db.commit()
    with sessions() as db, pytest.raises(Exception, match="reuse detected"):
        rotate_refresh_token(db, token=raw, settings=settings, user_agent=None, ip_address=None)
    with sessions() as db:
        assert all(token.revoked_at is not None for token in db.scalars(select(RefreshToken)).all())


def test_invalid_csrf_and_origin_do_not_logout(auth_app):
    app, sessions, settings = auth_app
    seed_rep(sessions)
    with TestClient(app) as client:
        client.post("/api/v1/auth/login", json={"email": "rep@example.edu", "password": "GoodPassword!123"})
        bad_csrf = client.post("/api/v1/auth/logout", headers={"Origin": "http://localhost:5173", "X-CSRF-Token": "wrong"})
        bad_origin = client.post("/api/v1/auth/logout", headers={**csrf_headers(client, settings), "Origin": "https://evil.example"})
        mismatched = client.post("/api/v1/auth/logout", headers={**csrf_headers(client, settings), "X-CSRF-Token": "not-the-cookie"})
    assert bad_csrf.status_code == 403
    assert bad_origin.status_code == 403
    assert mismatched.status_code == 403
    with sessions() as db:
        assert db.scalar(select(RefreshToken)).revoked_at is None


def test_logout_revokes_refresh_token_and_clears_both_cookies(auth_app):
    app, sessions, settings = auth_app
    seed_rep(sessions)
    with TestClient(app) as client:
        client.post("/api/v1/auth/login", json={"email": "rep@example.edu", "password": "GoodPassword!123"})
        response = client.post("/api/v1/auth/logout", headers=csrf_headers(client, settings))
    assert response.status_code == 200
    assert settings.refresh_cookie_name in response.headers["set-cookie"]
    assert settings.csrf_cookie_name in response.headers["set-cookie"]
    assert f'{settings.csrf_cookie_name}=""; expires=' in response.headers["set-cookie"]
    assert "Path=/; SameSite=lax" in response.headers["set-cookie"]
    with sessions() as db:
        assert db.scalar(select(RefreshToken)).revoked_at is not None


def test_authentication_rejects_inactive_users_and_stale_access_claims(auth_app):
    app, sessions, _settings = auth_app
    user_id, _ = seed_rep(sessions)
    with TestClient(app) as client:
        login = client.post("/api/v1/auth/login", json={"email": "rep@example.edu", "password": "GoodPassword!123"})
        access = login.json()["data"]["access_token"]
        with sessions.begin() as db:
            db.get(User, user_id).is_active = False
        assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"}).status_code == 401
        assert client.post("/api/v1/auth/login", json={"email": "rep@example.edu", "password": "GoodPassword!123"}).status_code == 401


def test_access_endpoint_rejects_missing_expired_invalid_signature_and_missing_claims(auth_app):
    app, sessions, settings = auth_app
    seed_rep(sessions)
    now = datetime.now(timezone.utc)
    base_claims = {"sub": "1", "role": "college_representative", "college_id": 1,
                   "token_type": "access", "iss": settings.jwt_issuer,
                   "aud": settings.jwt_audience, "iat": now, "exp": now + timedelta(minutes=1)}
    expired = jwt.encode({**base_claims, "exp": now - timedelta(seconds=1)}, settings.jwt_secret_key, algorithm="HS256")
    bad_signature = jwt.encode(base_claims, "different-signing-secret-with-32-bytes", algorithm="HS256")
    missing_claim = jwt.encode({"sub": "1", "exp": now + timedelta(minutes=1)}, settings.jwt_secret_key, algorithm="HS256")
    with pytest.raises(jwt.MissingRequiredClaimError):
        decode_access_token(missing_claim, settings)
    with TestClient(app) as client:
        missing = client.get("/api/v1/auth/me")
        expired_response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
        invalid_signature = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {bad_signature}"})
    assert missing.status_code == 401
    assert expired_response.status_code == 401
    assert invalid_signature.status_code == 401


def test_stale_college_claim_does_not_override_persisted_user(auth_app):
    app, sessions, _settings = auth_app
    user_id, _college_id = seed_rep(sessions)
    with sessions.begin() as db:
        other = College(name="Other College", address="Road", city="Pune", contact_email="office@other.edu")
        db.add(other)
    with TestClient(app) as client:
        access = client.post("/api/v1/auth/login", json={"email": "rep@example.edu", "password": "GoodPassword!123"}).json()["data"]["access_token"]
        with sessions.begin() as db:
            user = db.get(User, user_id)
            user.college_id = db.scalar(select(College.id).where(College.name == "Other College"))
        response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert response.status_code == 401


def test_inactive_user_cannot_refresh(auth_app):
    app, sessions, settings = auth_app
    user_id, _ = seed_rep(sessions)
    with TestClient(app) as client:
        client.post("/api/v1/auth/login", json={"email": "rep@example.edu", "password": "GoodPassword!123"})
        headers = csrf_headers(client, settings)
        with sessions.begin() as db:
            db.get(User, user_id).is_active = False
        response = client.post("/api/v1/auth/refresh", headers=headers)
    assert response.status_code == 401


def test_expired_active_refresh_is_revoked_and_rejected(auth_app):
    _app, sessions, settings = auth_app
    user_id, _ = seed_rep(sessions)
    with sessions() as db:
        raw, row = issue_refresh_token(db, user=db.get(User, user_id), settings=settings)
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    from fastapi import HTTPException
    with sessions() as db, pytest.raises(HTTPException) as error:
        rotate_refresh_token(db, token=raw, settings=settings, user_agent=None, ip_address=None)
    assert error.value.status_code == 401
    with sessions() as db:
        assert db.scalar(select(RefreshToken)).revoked_at is not None


def test_refresh_rejects_invalid_signature(auth_app):
    app, sessions, settings = auth_app
    seed_rep(sessions)
    fake_token = jwt.encode({"sub": "1", "jti": "fake", "fid": "fake", "token_type": "refresh",
                             "iss": settings.jwt_issuer, "aud": settings.jwt_audience,
                             "iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(days=1)},
                            "wrong-signature-key-with-extra-entropy-32chars", algorithm="HS256")
    csrf = issue_csrf_token(secret=settings.csrf_secret_key, refresh_token=fake_token)
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/refresh", headers={
            "Origin": "http://localhost:5173", "X-CSRF-Token": csrf,
            "Cookie": f"{settings.refresh_cookie_name}={fake_token}; {settings.csrf_cookie_name}={csrf}",
        })
    assert response.status_code == 401


def test_concurrent_refresh_attempts_cannot_issue_two_successful_replacements(auth_app):
    _app, sessions, settings = auth_app
    user_id, _ = seed_rep(sessions)
    with sessions() as db:
        user = db.get(User, user_id)
        raw, _row = issue_refresh_token(db, user=user, settings=settings)
        db.commit()

    def attempt():
        with sessions() as db:
            try:
                rotate_refresh_token(db, token=raw, settings=settings, user_agent=None, ip_address=None)
                return "success"
            except Exception:
                return "rejected"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert results.count("success") == 1
    with sessions() as db:
        tokens = db.scalars(select(RefreshToken)).all()
        assert len(tokens) == 2
        assert all(token.revoked_at is not None for token in tokens)


def test_provisioning_is_one_time_and_creates_global_admin(auth_app):
    _app, sessions, _settings = auth_app
    with sessions() as db:
        admin = provision_platform_admin(db, name="Initial Admin", email="admin@example.edu", password="GoodPassword!123")
        assert admin.role == "platform_admin" and admin.college_id is None
        assert verify_password("GoodPassword!123", admin.password_hash)
        with pytest.raises(ValueError, match="already exists"):
            provision_platform_admin(db, name="Second Admin", email="second@example.edu", password="GoodPassword!123")


def test_college_scoping_and_last_representative_protection(auth_app):
    app, sessions, _settings = auth_app
    user_id, college_id = seed_rep(sessions)
    with TestClient(app) as client:
        access = client.post("/api/v1/auth/login", json={"email": "rep@example.edu", "password": "GoodPassword!123"}).json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {access}"}
        status = client.patch(f"/api/v1/users/{user_id}/status", json={"is_active": False}, headers=headers)
        outside = client.get("/api/v1/colleges/999", headers=headers)
        own = client.get(f"/api/v1/colleges/{college_id}", headers=headers)
    assert status.status_code == 409
    assert outside.status_code == 404
    assert own.status_code == 200


def test_representative_can_create_and_manage_only_own_college_users(auth_app):
    app, sessions, _settings = auth_app
    user_id, college_id = seed_rep(sessions)
    with TestClient(app) as client:
        access = client.post("/api/v1/auth/login", json={"email": "rep@example.edu", "password": "GoodPassword!123"}).json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {access}"}
        created = client.post("/api/v1/colleges/me/users", headers=headers, json={
            "name": "Additional Rep", "email": "new.rep@example.edu", "password": "AnotherPassword!234"})
        assert created.status_code == 201, created.text
        assert "password_hash" not in created.text
        assert created.json()["data"]["college_id"] == college_id
        listed = client.get("/api/v1/colleges/me/users", headers=headers)
        injected = client.patch("/api/v1/users/me", headers=headers, json={"role": "platform_admin", "college_id": 999})
        profile = client.patch("/api/v1/users/me", headers=headers, json={"name": "Updated Rep"})
    assert len(listed.json()["data"]["items"]) == 2
    assert injected.status_code == 422
    assert profile.status_code == 200
    with sessions() as db:
        created_user = db.scalar(select(User).where(User.email == "new.rep@example.edu"))
        assert created_user.role == "college_representative"
        assert created_user.password_hash != "AnotherPassword!234"
        assert db.get(User, user_id).role == "college_representative"


def test_platform_admin_can_list_colleges_and_verify_them(auth_app):
    app, sessions, _settings = auth_app
    _rep_id, college_id = seed_rep(sessions, status="pending")
    with sessions() as db:
        admin = provision_platform_admin(db, name="Admin", email="admin@example.edu", password="AdminPassword!234")
        admin_id = admin.id
    with TestClient(app) as client:
        access = client.post("/api/v1/auth/login", json={"email": "admin@example.edu", "password": "AdminPassword!234"}).json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {access}"}
        listed = client.get("/api/v1/colleges", headers=headers)
        verified = client.patch(f"/api/v1/admin/colleges/{college_id}/verification", headers=headers,
                                json={"verification_status": "verified"})
        invalid = client.patch(f"/api/v1/admin/colleges/{college_id}/verification", headers=headers,
                               json={"verification_status": "pending"})
    assert listed.status_code == 200
    assert verified.status_code == 200
    assert verified.json()["data"]["verification_status"] == "verified"
    assert invalid.status_code == 422
    with sessions() as db:
        assert db.get(User, admin_id).college_id is None


def test_non_admin_cannot_verify_or_list_global_colleges(auth_app):
    app, sessions, _settings = auth_app
    _user_id, college_id = seed_rep(sessions, status="pending")
    with TestClient(app) as client:
        access = client.post("/api/v1/auth/login", json={"email": "rep@example.edu", "password": "GoodPassword!123"}).json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {access}"}
        verify = client.patch(f"/api/v1/admin/colleges/{college_id}/verification", headers=headers,
                              json={"verification_status": "verified"})
        listing = client.get("/api/v1/colleges", headers=headers)
    assert verify.status_code == 403
    assert listing.status_code == 403


def test_production_settings_require_secure_cookies_and_distinct_secrets():
    strong = "random-production-secret-material-0123456789"
    with pytest.raises(ValueError, match="CSRF secrets may only be used"):
        Settings(_env_file=None, environment="production", jwt_secret_key=strong,
                 csrf_secret_key="local-development-only-csrf-change-me", cookie_secure=True)
    with pytest.raises(ValueError, match="COOKIE_SECURE"):
        Settings(_env_file=None, environment="production", jwt_secret_key=strong,
                 csrf_secret_key="independent-production-csrf-secret-0123456789", cookie_secure=False)
    settings = Settings(_env_file=None, environment="production", jwt_secret_key=strong,
                         csrf_secret_key="independent-production-csrf-secret-0123456789",
                         cookie_secure=True)
    assert settings.cookie_secure and settings.cookie_samesite == "lax"
    with pytest.raises(ValueError, match="must be independent"):
        Settings(_env_file=None, jwt_secret_key="same-secret-material-for-both-keys",
                 csrf_secret_key="same-secret-material-for-both-keys")


def test_production_login_sets_secure_refresh_and_csrf_cookies(auth_app):
    app, sessions, _settings = auth_app
    seed_rep(sessions)
    production = Settings(
        _env_file=None, environment="production",
        jwt_secret_key="random-production-jwt-secret-material-0123456789",
        csrf_secret_key="independent-production-csrf-secret-0123456789",
        cookie_secure=True, cors_origins=["http://localhost:5173"],
    )
    app.dependency_overrides[get_settings] = lambda: production
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/login", json={"email": "rep@example.edu", "password": "GoodPassword!123"})
    assert response.status_code == 200
    cookies = response.headers.get_list("set-cookie")
    refresh_cookie = next(value for value in cookies if value.startswith(production.refresh_cookie_name + "="))
    csrf_cookie = next(value for value in cookies if value.startswith(production.csrf_cookie_name + "="))
    assert "Secure" in refresh_cookie and "HttpOnly" in refresh_cookie
    assert "Secure" in csrf_cookie and "HttpOnly" not in csrf_cookie


def test_admin_provisioning_route_does_not_exist(auth_app):
    app, _sessions, _settings = auth_app
    paths = app.openapi()["paths"]
    assert not any("provision" in path.lower() or "admin/register" in path.lower() for path in paths)


def test_admin_provisioning_cli_prompts_hidden_and_does_not_print_password(auth_app, monkeypatch, capsys):
    _app, sessions, _settings = auth_app
    from app import cli
    answers = iter(["Provisioned Admin", "cli-admin@example.edu"])
    passwords = iter(["VerySecureAdmin!234", "VerySecureAdmin!234"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: next(passwords))
    monkeypatch.setattr(cli, "SessionLocal", sessions)
    assert cli.provision_admin() == 0
    out = capsys.readouterr()
    assert "VerySecureAdmin!234" not in out.out + out.err
    with sessions() as db:
        admin = db.scalar(select(User).where(User.email == "cli-admin@example.edu"))
        assert admin.role == "platform_admin" and admin.college_id is None


def test_refresh_transaction_rolls_back_if_replacement_creation_fails(auth_app, monkeypatch):
    _app, sessions, settings = auth_app
    user_id, _ = seed_rep(sessions)
    with sessions() as db:
        raw, _row = issue_refresh_token(db, user=db.get(User, user_id), settings=settings)
        db.commit()
    from app.services import auth as auth_service
    def fail_issue(*_args, **_kwargs):
        raise RuntimeError("simulated replacement failure")
    monkeypatch.setattr(auth_service, "issue_refresh_token", fail_issue)
    with sessions() as db, pytest.raises(RuntimeError, match="simulated replacement failure"):
        rotate_refresh_token(db, token=raw, settings=settings, user_agent=None, ip_address=None)
    with sessions() as db:
        rows = db.scalars(select(RefreshToken)).all()
        assert len(rows) == 1 and rows[0].revoked_at is None


def test_failed_login_uses_generic_message_and_does_not_log_secret(auth_app, caplog):
    app, sessions, _settings = auth_app
    seed_rep(sessions)
    secret = "DeliberatelyWrong!123"
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/login", json={"email": "rep@example.edu", "password": secret})
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Email or password is incorrect."
    assert secret not in caplog.text


def test_wildcard_cors_is_rejected_with_credential_support():
    with pytest.raises(ValueError, match="Wildcard CORS origins"):
        Settings(_env_file=None, cors_origins=["*"])


def test_verified_college_guard_is_reusable(auth_app):
    _app, sessions, _settings = auth_app
    _user_id, college_id = seed_rep(sessions, status="pending")
    from app.core.authorization import require_verified_college
    from fastapi import HTTPException
    with sessions() as db, pytest.raises(HTTPException) as exc:
        require_verified_college(db, college_id)
    assert exc.value.status_code == 403
