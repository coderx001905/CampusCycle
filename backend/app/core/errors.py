import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class APIError(StarletteHTTPException):
    """HTTP error carrying a stable application error code."""

    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(status_code=status_code, detail=message)
        self.error_code = code


def _error_payload(code: str, message: str, details: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
        }
    }


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = [
        {
            "location": list(error.get("loc", ())),
            "message": error.get("msg", "Invalid value"),
            "type": error.get("type", "value_error"),
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=_error_payload("validation_error", "Request validation failed.", details),
    )


async def http_error_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    code_by_status = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        413: "payload_too_large",
    }
    detail = exc.detail if isinstance(exc.detail, str) else "The request could not be processed."
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content=_error_payload(
            getattr(exc, "error_code", code_by_status.get(exc.status_code, "http_error")),
            detail,
        ),
    )


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled API error for %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=_error_payload("internal_server_error", "An unexpected error occurred."),
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)
