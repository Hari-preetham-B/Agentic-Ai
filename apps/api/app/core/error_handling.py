"""Error handling middleware and structured error responses."""

from __future__ import annotations

import traceback
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)


class StructuredErrorMiddleware(BaseHTTPMiddleware):
    """Middleware that converts unhandled exceptions into structured JSON errors."""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unhandled exception: %s", exc)
            settings = get_settings()
            is_dev = settings.environment == "development"

            error_body: dict[str, Any] = {
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred.",
                }
            }
            if is_dev:
                error_body["error"]["details"] = {
                    "exception": str(exc),
                    "traceback": traceback.format_exc().split("\n")[-5:],
                }

            return JSONResponse(
                status_code=500,
                content=error_body,
            )


def register_error_handlers(app: FastAPI) -> None:
    """Register structured error handlers on the FastAPI app."""

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": str(exc),
                }
            },
        )

    @app.exception_handler(PermissionError)
    async def permission_error_handler(request: Request, exc: PermissionError):
        return JSONResponse(
            status_code=403,
            content={
                "error": {
                    "code": "FORBIDDEN",
                    "message": str(exc),
                }
            },
        )

    @app.exception_handler(LookupError)
    async def lookup_error_handler(request: Request, exc: LookupError):
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "NOT_FOUND",
                    "message": str(exc),
                }
            },
        )


__all__ = ["StructuredErrorMiddleware", "register_error_handlers"]
