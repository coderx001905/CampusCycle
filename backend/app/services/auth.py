import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.passwords import hash_password, verify_password
from app.core.security import create_access_token
from app.models import College, RefreshToken, User

logger = logging.getLogger(__name__)
GENERIC_LOGIN_ERROR = "Email or password is incorrect."


def _now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def safe_user(user: User) -> dict[str, object]:
    return {"id": user.id, "name": user.name, "email": user.email,
            "role": user.role, "college_id": user.college_id, "is_active": user.is_active}


def register_college(db: Session, *, college_data: dict, representative_data: dict) -> tuple[College, User]:
    try:
        with db.begin():
            college = College(**college_data, verification_status="pending")
            representative = User(
                name=representative_data["name"],
                email=normalize_email(representative_data["email"]),
                password_hash=hash_password(representative_data["password"]),
                role="college_representative",
                college=college,
            )
            db.add_all([college, representative])
            db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists.") from exc
    return college, representative


def provision_platform_admin(db: Session, *, name: str, email: str, password: str) -> User:
    """Create the sole initial admin under a SQLite write lock where applicable."""
    try:
        if db.bind is not None and db.bind.dialect.name == "sqlite":
            db.connection().exec_driver_sql("BEGIN IMMEDIATE")
        else:
            db.begin()
        existing = db.scalar(select(User.id).where(User.role == "platform_admin").limit(1))
        if existing is not None:
            db.rollback()
            raise ValueError("A Platform Admin already exists; provisioning is one-time only.")
        user = User(name=name.strip(), email=normalize_email(email), password_hash=hash_password(password),
                    role="platform_admin", college_id=None)
        db.add(user)
        db.commit()
        return user
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("Platform Admin provisioning conflicted with another account change.") from exc
    except Exception:
        db.rollback()
        raise


def issue_refresh_token(db: Session, *, user: User, settings: Settings,
                        user_agent: str | None = None, ip_address: str | None = None,
                        family_id: str | None = None) -> tuple[str, RefreshToken]:
    now = _now()
    jti = secrets.token_urlsafe(24)
    family = family_id or secrets.token_urlsafe(24)
    expiry = now + timedelta(days=settings.refresh_token_expire_days)
    token = jwt.encode({
        "sub": str(user.id), "jti": jti, "fid": family, "token_type": "refresh",
        "iss": settings.jwt_issuer, "aud": settings.jwt_audience,
        "iat": now, "exp": expiry,
    }, settings.jwt_secret_key, algorithm="HS256")
    row = RefreshToken(user_id=user.id, token_hash=hashlib.sha256(token.encode()).hexdigest(),
                       jti=jti, token_family_id=family, expires_at=expiry,
                       user_agent=(user_agent or "")[:500] or None,
                       ip_address=(ip_address or "")[:64] or None)
    db.add(row)
    db.flush()
    return token, row


def decode_refresh_token(token: str, settings: Settings, *, verify_expiry: bool = True) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"],
                      issuer=settings.jwt_issuer, audience=settings.jwt_audience,
                      options={"require": ["exp", "iat", "sub", "jti", "fid", "iss", "aud", "token_type"],
                               "verify_exp": verify_expiry})


def _revoke_family(db: Session, family_id: str, now: datetime) -> None:
    db.execute(update(RefreshToken).where(
        RefreshToken.token_family_id == family_id, RefreshToken.revoked_at.is_(None)
    ).values(revoked_at=now).execution_options(synchronize_session=False))


def rotate_refresh_token(db: Session, *, token: str, settings: Settings,
                         user_agent: str | None, ip_address: str | None) -> tuple[str, User]:
    expired_claim = False
    try:
        claims = decode_refresh_token(token, settings)
        user_id = int(claims["sub"])
    except jwt.ExpiredSignatureError:
        try:
            claims = decode_refresh_token(token, settings, verify_expiry=False)
            user_id = int(claims["sub"])
            expired_claim = True
        except Exception as exc:
            raise HTTPException(status_code=401, detail="Session is invalid; sign in again.") from exc
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Session is invalid; sign in again.") from exc
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    now = _now()
    reused = False
    expired = False
    inactive = False
    result: tuple[str, User] | None = None
    try:
        with db.begin():
            if db.bind is not None and db.bind.dialect.name == "sqlite":
                db.connection().exec_driver_sql("BEGIN IMMEDIATE")
            row = db.scalar(select(RefreshToken).where(RefreshToken.jti == claims["jti"]))
            if row is None or row.user_id != user_id or row.token_family_id != claims["fid"] or not secrets.compare_digest(row.token_hash, token_hash):
                raise HTTPException(status_code=401, detail="Session is invalid; sign in again.")
            if row.revoked_at is not None:
                if row.replaced_by_token_id is not None:
                    _revoke_family(db, row.token_family_id, now)
                    reused = True
                else:
                    raise HTTPException(status_code=401, detail="Session is invalid; sign in again.")
            elif expired_claim or row.expires_at <= now:
                row.revoked_at = now
                expired = True
            else:
                user = db.get(User, row.user_id)
                if user is None or not user.is_active:
                    _revoke_family(db, row.token_family_id, now)
                    inactive = True
                    user = None
                if user is not None:
                    changed = db.execute(update(RefreshToken).where(
                    RefreshToken.id == row.id, RefreshToken.revoked_at.is_(None)
                    ).values(revoked_at=now).execution_options(synchronize_session=False)).rowcount
                    if changed != 1:
                        _revoke_family(db, row.token_family_id, now)
                        reused = True
                    else:
                        replacement, replacement_row = issue_refresh_token(
                            db, user=user, settings=settings, user_agent=user_agent,
                            ip_address=ip_address, family_id=row.token_family_id)
                        db.execute(update(RefreshToken).where(
                            RefreshToken.id == row.id, RefreshToken.replaced_by_token_id.is_(None)
                        ).values(replaced_by_token_id=replacement_row.id).execution_options(synchronize_session=False))
                        result = (replacement, user)
    except HTTPException:
        raise
    if reused:
        raise HTTPException(status_code=401, detail="Session reuse detected; sign in again.")
    if expired:
        raise HTTPException(status_code=401, detail="Session has expired; sign in again.")
    if inactive:
        raise HTTPException(status_code=401, detail="Session is invalid; sign in again.")
    assert result is not None
    return result


def revoke_refresh_token(db: Session, token: str, settings: Settings) -> None:
    try:
        claims = decode_refresh_token(token, settings)
    except jwt.ExpiredSignatureError:
        try:
            claims = decode_refresh_token(token, settings, verify_expiry=False)
        except Exception:
            return
    except Exception:
        return
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    row = db.scalar(select(RefreshToken).where(RefreshToken.jti == claims["jti"]))
    if row and secrets.compare_digest(row.token_hash, token_hash) and row.revoked_at is None:
        row.revoked_at = _now()
        db.commit()


def authenticate_user(db: Session, *, email: str, password: str) -> User:
    user = db.scalar(select(User).where(func.lower(User.email) == normalize_email(email)))
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail=GENERIC_LOGIN_ERROR, headers={"WWW-Authenticate": "Bearer"})
    return user


def make_access_response(user: User, settings: Settings) -> dict[str, object]:
    access = create_access_token(subject=str(user.id), role=user.role,
                                 college_id=user.college_id, settings=settings)
    return {"access_token": access, "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
            "user": safe_user(user)}
