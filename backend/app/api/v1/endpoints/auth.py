import hmac

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.core.authorization import get_current_user
from app.core.config import Settings, get_settings
from app.core.csrf import issue_csrf_token, verify_csrf_token
from app.db.session import get_db
from app.models import User
from app.schemas.accounts import CollegeRegistrationInput, LoginInput
from app.services.auth import (
    authenticate_user,
    make_access_response,
    issue_refresh_token,
    register_college,
    revoke_refresh_token,
    rotate_refresh_token,
    safe_user,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


def _cookie(response: Response, settings: Settings, *, refresh: str, csrf: str, max_age: int) -> None:
    common = {"max_age": max_age, "domain": settings.cookie_domain or None, "secure": settings.cookie_secure,
              "samesite": settings.cookie_samesite}
    response.set_cookie(settings.refresh_cookie_name, refresh, httponly=True,
                        path=settings.auth_cookie_path, **common)
    response.set_cookie(settings.csrf_cookie_name, csrf, httponly=False,
                        path=settings.csrf_cookie_path, **common)


def _clear_cookies(response: Response, settings: Settings) -> None:
    for name in (settings.refresh_cookie_name, settings.csrf_cookie_name):
        path = settings.auth_cookie_path if name == settings.refresh_cookie_name else settings.csrf_cookie_path
        response.delete_cookie(name, path=path, domain=settings.cookie_domain or None,
                                secure=settings.cookie_secure, httponly=(name == settings.refresh_cookie_name),
                                samesite=settings.cookie_samesite)


def _validate_origin_and_csrf(request: Request, settings: Settings, refresh: str) -> None:
    origin = request.headers.get("origin")
    if not origin or origin not in settings.cors_origins:
        raise HTTPException(status_code=403, detail="Request origin is not allowed.")
    cookie_token = request.cookies.get(settings.csrf_cookie_name)
    header_token = request.headers.get("X-CSRF-Token")
    if (not cookie_token or not header_token or
            not hmac.compare_digest(cookie_token, header_token) or
            not verify_csrf_token(token=cookie_token, secret=settings.csrf_secret_key,
                                  refresh_token=refresh)):
        raise HTTPException(status_code=403, detail="CSRF validation failed.")


@router.post("/register", status_code=201)
def register(payload: CollegeRegistrationInput, db: Session = Depends(get_db)) -> dict:
    college_data = payload.college.model_dump()
    representative_data = payload.representative.model_dump()
    college, user = register_college(db, college_data=college_data,
                                     representative_data=representative_data)
    return {"success": True, "data": {
        "college": {"id": college.id, "name": college.name,
                    "verification_status": college.verification_status},
        "user": safe_user(user),
    }}


@router.post("/login")
def login(payload: LoginInput, request: Request, response: Response,
          db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> dict:
    user = authenticate_user(db, email=str(payload.email), password=payload.password)
    try:
        refresh, _ = issue_refresh_token(
            db, user=user, settings=settings,
            user_agent=None,
            ip_address=None,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    csrf = issue_csrf_token(secret=settings.csrf_secret_key, refresh_token=refresh)
    _cookie(response, settings, refresh=refresh, csrf=csrf,
            max_age=settings.refresh_token_expire_days * 86400)
    return {"success": True, "data": make_access_response(user, settings)}


@router.post("/refresh")
def refresh(request: Request, response: Response, db: Session = Depends(get_db),
            settings: Settings = Depends(get_settings)) -> dict:
    raw = request.cookies.get(settings.refresh_cookie_name)
    if not raw:
        raise HTTPException(status_code=401, detail="Session is invalid; sign in again.")
    _validate_origin_and_csrf(request, settings, raw)
    replacement, user = rotate_refresh_token(
        db, token=raw, settings=settings,
        user_agent=None,
        ip_address=None,
    )
    csrf = issue_csrf_token(secret=settings.csrf_secret_key, refresh_token=replacement)
    _cookie(response, settings, refresh=replacement, csrf=csrf,
            max_age=settings.refresh_token_expire_days * 86400)
    return {"success": True, "data": make_access_response(user, settings)}


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db),
           settings: Settings = Depends(get_settings)) -> dict:
    raw = request.cookies.get(settings.refresh_cookie_name)
    if not raw:
        _clear_cookies(response, settings)
        raise HTTPException(status_code=401, detail="Session is invalid; sign in again.")
    _validate_origin_and_csrf(request, settings, raw)
    revoke_refresh_token(db, raw, settings)
    _clear_cookies(response, settings)
    return {"success": True, "data": {"message": "Logged out successfully."}}


@router.get("/me")
def auth_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    college = user.college
    return {"success": True, "data": {
        "user": safe_user(user),
        "college": ({"id": college.id, "name": college.name,
                     "verification_status": college.verification_status} if college else None),
    }}
