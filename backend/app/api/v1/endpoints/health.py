import logging

from fastapi import APIRouter
from fastapi import Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health", tags=["health"])
def health_check() -> dict[str, object]:
    """Report that the API process is responding."""
    return {"success": True, "data": {"status": "ok"}}


@router.get("/ready", tags=["health"], response_model=None)
def readiness_check(db: Session = Depends(get_db)) -> dict[str, object] | JSONResponse:
    """Report whether the API can communicate with its configured database."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("Database readiness check failed")
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "database_unavailable",
                    "message": "The database is unavailable.",
                    "details": [],
                }
            },
        )

    return {"success": True, "data": {"status": "ready"}}
