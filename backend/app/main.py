"""FastAPI application entry point.

Run locally:  uvicorn app.main:app --reload   (from the backend/ directory)
Interactive docs: http://localhost:8000/docs
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import dashboard, health, inventory, orders, products
from app.api import categories, customers, suppliers
from app.config import settings
from app.migrations_runner import run_migrations
from app.services.exceptions import AppError

logger = logging.getLogger("shopstock")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.app_env != "test":
        run_migrations()
    yield


def create_app() -> FastAPI:
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Small Business Inventory & Order Management System",
        lifespan=lifespan,
        debug=False,  # never run debug mode, regardless of environment
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(categories.router)
    app.include_router(suppliers.router)
    app.include_router(customers.router)
    app.include_router(products.router)
    app.include_router(inventory.router)
    app.include_router(orders.router)
    app.include_router(dashboard.router)

    _register_exception_handlers(app)
    return app


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(part) for part in first.get("loc", []) if part != "body")
        message = f"{loc}: {first.get('msg', 'invalid input')}" if loc else "Invalid request payload."
        details = [
            {"loc": [str(p) for p in err.get("loc", [])], "msg": err.get("msg", ""), "type": err.get("type", "")}
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "validation_error", "message": message, "details": details}},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_: Request, exc: Exception):
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error",
                               "message": "An unexpected error occurred."}},
        )


app = create_app()
