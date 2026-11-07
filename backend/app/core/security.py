from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.core.config import Settings


def create_access_token(
    *,
    subject: str,
    role: str,
    college_id: int | None,
    settings: Settings,
) -> str:
    """Create a signed V1 access token; authentication endpoints are not included."""
    now = datetime.now(timezone.utc)
    claims: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "college_id": college_id,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    """Verify a signed access token and its expiry using the configured algorithm."""
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        options={"require": ["exp", "iat", "sub", "iss", "aud"]},
    )
