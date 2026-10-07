# File path: backend/core/errors.py
"""
Centralized error handling.

Every error response from this API has the same shape:
    {"success": false, "error": {"code": "...", "message": "..."}}

AppError is a thin HTTPException subclass that adds a machine-readable
`code` (e.g. "CAMPAIGN_NOT_FOUND") alongside the human-readable message.
Services should raise AppError instead of plain HTTPException going
forward -- existing plain HTTPException raises still work (a generic
code is filled in automatically), so nothing breaks immediately, but new
code should use AppError for a meaningful `code` field.

register_exception_handlers(app) wires up three handlers:
  * AppError            -> the shape above, using its own code/message
  * HTTPException        -> the shape above, with a generic code derived
                             from the status (e.g. 404 -> "NOT_FOUND")
  * any other Exception  -> logged in full server-side, but the client
                             only ever sees a generic 500 message --
                             never a stack trace or internal detail
"""

import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

_GENERIC_CODES_BY_STATUS = {
    status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
    status.HTTP_403_FORBIDDEN: "FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_422_UNPROCESSABLE_CONTENT: "VALIDATION_ERROR",
}


class AppError(HTTPException):
    """Raise this (instead of plain HTTPException) for a response with a
    specific, meaningful error code:

        raise AppError(
            status_code=404,
            code="CAMPAIGN_NOT_FOUND",
            message="Campaign not found.",
        )
    """

    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.message = message


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "error": {"code": code, "message": message}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return _error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(HTTPException)
    async def handle_http_exception(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        # Plain HTTPException (raised by existing service code, or by
        # FastAPI/Starlette itself) -- no explicit `code`, so derive a
        # reasonable generic one from the status.
        code = _GENERIC_CODES_BY_STATUS.get(exc.status_code, "ERROR")
        message = exc.detail if isinstance(exc.detail, str) else "An error occurred."
        return _error_response(exc.status_code, code, message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Pydantic's default validation error body isn't in our shape --
        # normalize it, but keep exc.errors() in the message for
        # debuggability (it describes which field was invalid, not
        # anything secret).
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "VALIDATION_ERROR",
            f"Invalid request: {exc.errors()}",
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # Anything NOT already handled above (a raw DB error, a bug, etc).
        # Full detail goes to the server log only -- the client never
        # sees internals.
        logger.exception("Unhandled exception on %s %s", request.method, request.url)
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_ERROR",
            "An unexpected error occurred.",
        )