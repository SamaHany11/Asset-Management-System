
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# Maps common HTTP status codes to a stable machine-readable error code.
# Plain integers are used (rather than fastapi.status constants) so this
# stays stable across FastAPI versions that rename/deprecate constants.
STATUS_CODE_NAMES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    500: "INTERNAL_ERROR",
}


def _error_body(code: str, message: str, details=None) -> dict:
    body = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return body


def register_exception_handlers(app) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        return JSONResponse(
            status_code=422,
            content=_error_body(
                code="VALIDATION_ERROR",
                message="One or more fields failed validation.",
                details=exc.errors(),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ):
        code = STATUS_CODE_NAMES.get(exc.status_code, "ERROR")
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(code=code, message=str(exc.detail)),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # Never leak internals (stack traces, query text, secrets) to the
        # client — this is a security product, per the task's ground rules.
        return JSONResponse(
            status_code=500,
            content=_error_body(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred.",
            ),
        )
