"""Clean error responses; technical details go to the log only."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from backend.core.exceptions import AppError
from backend.core.logging_config import get_logger

log = get_logger("errors")


def register_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error(_: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message, "code": exc.code})

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        msgs = [f"{'.'.join(str(x) for x in e['loc'][1:])}: {e['msg']}" for e in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": "Invalid request. " + "; ".join(msgs), "code": "invalid_request"})

    @app.exception_handler(OperationalError)
    async def db_unavailable(_: Request, exc: OperationalError):
        log.error("database unavailable", exc_info=exc)
        return JSONResponse(status_code=503, content={"detail": "The database is temporarily unavailable.", "code": "database_unavailable"})

    @app.exception_handler(SQLAlchemyError)
    async def db_error(_: Request, exc: SQLAlchemyError):
        log.error("database error", exc_info=exc)
        return JSONResponse(status_code=500, content={"detail": "A database error occurred.", "code": "database_error"})

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception):
        log.error("unhandled error", exc_info=exc)
        return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred.", "code": "internal_error"})
