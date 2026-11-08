from datetime import datetime, timezone
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app import cli
from app.core.config import Settings
from app.core.passwords import hash_password
from app.db.session import create_database_engine
from app.models import Base, College, RefreshToken, User
from app.services.auth import (
    authenticate_user,
    issue_refresh_token,
    provision_platform_admin,
    reset_platform_admin_password,
)


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_cli_admin.sqlite3"
    engine = create_database_engine(f"sqlite:///{db_file.as_posix()}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    settings = Settings(
        _env_file=None,
        jwt_secret_key="cli-test-jwt-secret-with-sufficient-entropy-1234",
        csrf_secret_key="cli-test-csrf-secret-with-sufficient-entropy-1234",
        cors_origins=["http://localhost:5173"],
    )
    try:
        yield session_factory, settings
    finally:
        engine.dispose()


def test_reset_admin_password_success(test_db, monkeypatch, capsys):
    sessions, settings = test_db
    with sessions() as db:
        admin = provision_platform_admin(db, name="Primary Admin", email="admin@example.edu", password="InitialPassword!123")
        # Issue refresh token for admin
        issue_refresh_token(db, user=admin, settings=settings)

        # Create a representative user with a refresh token
        college = College(name="Test College", address="Street 1", city="City",
                          contact_email="test@example.edu", verification_status="verified")
        rep = User(name="Rep User", email="rep@example.edu", password_hash=hash_password("RepPassword!123"),
                   role="college_representative", college=college, is_active=True)
        db.add_all([college, rep])
        db.flush()
        issue_refresh_token(db, user=rep, settings=settings)
        db.commit()

    # Configure CLI mock
    passwords = iter(["NewSecurePassword!2026", "NewSecurePassword!2026"])
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: next(passwords))
    monkeypatch.setattr(cli, "SessionLocal", sessions)

    exit_code = cli.reset_admin_password()
    assert exit_code == 0

    out = capsys.readouterr()
    assert "Platform Admin password reset successfully; all active sessions revoked." in out.out
    # Passwords and hashes must never appear in output
    assert "NewSecurePassword!2026" not in out.out + out.err
    assert "InitialPassword!123" not in out.out + out.err
    assert "$argon2" not in out.out + out.err

    with sessions() as db:
        # New password authenticates
        authenticated = authenticate_user(db, email="admin@example.edu", password="NewSecurePassword!2026")
        assert authenticated.id == admin.id

        # Old password no longer authenticates
        with pytest.raises(HTTPException) as exc_info:
            authenticate_user(db, email="admin@example.edu", password="InitialPassword!123")
        assert exc_info.value.status_code == 401

        # Admin refresh tokens are revoked
        admin_tokens = db.scalars(select(RefreshToken).where(RefreshToken.user_id == admin.id)).all()
        assert len(admin_tokens) == 1
        assert admin_tokens[0].revoked_at is not None

        # Rep user refresh tokens remain active (unrevoked)
        rep_tokens = db.scalars(select(RefreshToken).where(RefreshToken.user_id == rep.id)).all()
        assert len(rep_tokens) == 1
        assert rep_tokens[0].revoked_at is None


def test_reset_admin_password_no_admin_exists(test_db, monkeypatch, capsys):
    sessions, _settings = test_db
    passwords = iter(["NewSecurePassword!2026", "NewSecurePassword!2026"])
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: next(passwords))
    monkeypatch.setattr(cli, "SessionLocal", sessions)

    exit_code = cli.reset_admin_password()
    assert exit_code == 1

    out = capsys.readouterr()
    assert "No Platform Admin account exists; use 'provision-admin' to create one." in out.err


def test_reset_admin_password_multiple_admins(test_db, monkeypatch, capsys):
    sessions, _settings = test_db
    with sessions() as db:
        admin1 = User(name="Admin 1", email="admin1@example.edu", password_hash=hash_password("Pass1!1234567"),
                      role="platform_admin", college_id=None, is_active=True)
        admin2 = User(name="Admin 2", email="admin2@example.edu", password_hash=hash_password("Pass2!1234567"),
                      role="platform_admin", college_id=None, is_active=True)
        db.add_all([admin1, admin2])
        db.commit()

    passwords = iter(["NewSecurePassword!2026", "NewSecurePassword!2026"])
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: next(passwords))
    monkeypatch.setattr(cli, "SessionLocal", sessions)

    exit_code = cli.reset_admin_password()
    assert exit_code == 1

    out = capsys.readouterr()
    assert "Multiple Platform Admin accounts found; manual intervention required." in out.err


def test_reset_admin_password_inactive_admin(test_db, monkeypatch, capsys):
    sessions, _settings = test_db
    with sessions() as db:
        admin = User(name="Admin Inactive", email="inactive@example.edu", password_hash=hash_password("OldPassword!123"),
                     role="platform_admin", college_id=None, is_active=False)
        db.add(admin)
        db.commit()
        original_hash = admin.password_hash

    passwords = iter(["NewSecurePassword!2026", "NewSecurePassword!2026"])
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: next(passwords))
    monkeypatch.setattr(cli, "SessionLocal", sessions)

    exit_code = cli.reset_admin_password()
    assert exit_code == 1

    out = capsys.readouterr()
    assert "The Platform Admin account is inactive; cannot reset password." in out.err

    # Password hash must not be changed
    with sessions() as db:
        db_admin = db.get(User, admin.id)
        assert db_admin.password_hash == original_hash


def test_reset_admin_password_confirmation_mismatch(test_db, monkeypatch, capsys):
    sessions, _settings = test_db
    with sessions() as db:
        admin = provision_platform_admin(db, name="Admin", email="admin@example.edu", password="InitialPassword!123")
        original_hash = admin.password_hash

    passwords = iter(["NewSecurePassword!2026", "DifferentPassword!2026"])
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: next(passwords))
    monkeypatch.setattr(cli, "SessionLocal", sessions)

    exit_code = cli.reset_admin_password()
    assert exit_code == 2

    out = capsys.readouterr()
    assert "Passwords do not match." in out.err

    with sessions() as db:
        db_admin = db.get(User, admin.id)
        assert db_admin.password_hash == original_hash


def test_reset_admin_password_too_short(test_db, monkeypatch, capsys):
    sessions, _settings = test_db
    with sessions() as db:
        admin = provision_platform_admin(db, name="Admin", email="admin@example.edu", password="InitialPassword!123")
        original_hash = admin.password_hash

    passwords = iter(["Short!123", "Short!123"])  # 9 chars < 12
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: next(passwords))
    monkeypatch.setattr(cli, "SessionLocal", sessions)

    exit_code = cli.reset_admin_password()
    assert exit_code == 2

    out = capsys.readouterr()
    assert "Password must contain 12 to 128 characters." in out.err

    with sessions() as db:
        db_admin = db.get(User, admin.id)
        assert db_admin.password_hash == original_hash


def test_reset_admin_password_too_long(test_db, monkeypatch, capsys):
    sessions, _settings = test_db
    with sessions() as db:
        admin = provision_platform_admin(db, name="Admin", email="admin@example.edu", password="InitialPassword!123")
        original_hash = admin.password_hash

    long_pass = "A" * 129
    passwords = iter([long_pass, long_pass])
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: next(passwords))
    monkeypatch.setattr(cli, "SessionLocal", sessions)

    exit_code = cli.reset_admin_password()
    assert exit_code == 2

    out = capsys.readouterr()
    assert "Password must contain 12 to 128 characters." in out.err

    with sessions() as db:
        db_admin = db.get(User, admin.id)
        assert db_admin.password_hash == original_hash


def test_reset_admin_password_cli_failure_reports_error(test_db, monkeypatch, capsys):
    sessions, settings = test_db
    with sessions() as db:
        admin = provision_platform_admin(db, name="Admin", email="admin@example.edu", password="InitialPassword!123")
        issue_refresh_token(db, user=admin, settings=settings)
        db.commit()
        original_hash = admin.password_hash

    passwords = iter(["NewSecurePassword!2026", "NewSecurePassword!2026"])
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: next(passwords))
    monkeypatch.setattr(cli, "SessionLocal", sessions)

    def mock_db_failure(*_args, **_kwargs):
        raise RuntimeError("simulated disk write failure")

    monkeypatch.setattr(cli, "reset_platform_admin_password", mock_db_failure)

    exit_code = cli.reset_admin_password()
    assert exit_code == 1

    out = capsys.readouterr()
    assert "Platform Admin password reset failed." in out.err

    with sessions() as db:
        db_admin = db.get(User, admin.id)
        assert db_admin.password_hash == original_hash
        token = db.scalar(select(RefreshToken).where(RefreshToken.user_id == admin.id))
        assert token.revoked_at is None


def test_reset_platform_admin_password_service_rollback_on_db_error(test_db, monkeypatch):
    sessions, settings = test_db
    with sessions() as db:
        admin = provision_platform_admin(db, name="Admin", email="admin@example.edu", password="InitialPassword!123")
        issue_refresh_token(db, user=admin, settings=settings)
        db.commit()
        original_hash = admin.password_hash

    with sessions() as db:
        def fail_commit():
            raise RuntimeError("simulated commit failure")

        monkeypatch.setattr(db, "commit", fail_commit)
        with pytest.raises(RuntimeError, match="simulated commit failure"):
            reset_platform_admin_password(db, new_password="NewSecurePassword!2026")

    with sessions() as db:
        db_admin = db.get(User, admin.id)
        assert db_admin.password_hash == original_hash
        token = db.scalar(select(RefreshToken).where(RefreshToken.user_id == admin.id))
        assert token.revoked_at is None


def test_cli_main_dispatching(monkeypatch, capsys):
    import sys

    # No arguments
    monkeypatch.setattr(sys, "argv", ["app.cli"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2

    # Invalid command
    monkeypatch.setattr(sys, "argv", ["app.cli", "unknown-command"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2

    # Extra arguments on reset-admin-password
    monkeypatch.setattr(sys, "argv", ["app.cli", "reset-admin-password", "extra"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2

    # Extra arguments on provision-admin
    monkeypatch.setattr(sys, "argv", ["app.cli", "provision-admin", "extra"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
