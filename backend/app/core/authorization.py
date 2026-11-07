from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import College, User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authentication is required.", headers={"WWW-Authenticate": "Bearer"})
    try:
        claims = decode_access_token(credentials.credentials, settings)
        user_id = int(claims["sub"])
        if claims.get("token_type", "access") != "access":
            raise ValueError("Wrong token type")
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired access token.", headers={"WWW-Authenticate": "Bearer"}) from exc
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid or expired access token.", headers={"WWW-Authenticate": "Bearer"})
    # Reject stale authorization claims; the database remains the authority.
    try:
        token_college = claims.get("college_id")
        if token_college is not None:
            token_college = int(token_college)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid access token.") from exc
    if claims.get("role") != user.role or token_college != user.college_id:
        raise HTTPException(status_code=401, detail="Authorization changed; sign in again.")
    return user


def require_platform_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "platform_admin" or user.college_id is not None:
        raise HTTPException(status_code=403, detail="Platform administrator access is required.")
    return user


def require_college_representative(user: User = Depends(get_current_user)) -> User:
    if user.role != "college_representative" or user.college_id is None:
        raise HTTPException(status_code=403, detail="College representative access is required.")
    return user


def require_verified_college(db: Session, college_id: int) -> College:
    """Reusable eligibility guard for later transactional business services."""
    college = db.get(College, college_id)
    if college is None:
        raise HTTPException(status_code=404, detail="College not found.")
    if college.verification_status != "verified":
        raise HTTPException(status_code=403, detail="The college is not eligible to transact.")
    return college
