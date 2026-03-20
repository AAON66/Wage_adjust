from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.v1 import api_router
from backend.app.core.config import Settings, get_settings
from backend.app.core.logging import configure_logging
from backend.app.dependencies import get_app_settings

logger = logging.getLogger(__name__)


def build_error_response(
    *,
    status_code: int,
    error: str,
    message: str,
    details: object | None = None,
) -> JSONResponse:
    payload: dict[str, object] = {
        'error': error,
        'message': message,
    }
    if details is not None:
        payload['details'] = details
    return JSONResponse(status_code=status_code, content=payload)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    configure_logging(settings)
    logger.info('Starting %s v%s', settings.app_name, settings.app_version)
    yield
    logger.info('Stopping %s', settings.app_name)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        return build_error_response(
            status_code=exc.status_code,
            error='http_error',
            message=str(exc.detail),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return build_error_response(
            status_code=422,
            error='validation_error',
            message='Request validation failed.',
            details=exc.errors(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception('Unhandled application error', exc_info=exc)
        return build_error_response(
            status_code=500,
            error='internal_server_error',
            message='An unexpected error occurred.',
        )


def register_middlewares(app: FastAPI, settings: Settings) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )


def register_routes(app: FastAPI, settings: Settings) -> None:
    @app.get('/health', tags=['health'])
    async def health_check() -> dict[str, str]:
        return {
            'status': 'ok',
            'app_name': settings.app_name,
            'version': settings.app_version,
            'api_prefix': settings.api_v1_prefix,
        }

    app.include_router(api_router, prefix=settings.api_v1_prefix)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        debug=resolved_settings.debug,
        lifespan=lifespan,
    )
    app.dependency_overrides[get_app_settings] = lambda: resolved_settings
    register_middlewares(app, resolved_settings)
    register_exception_handlers(app)
    register_routes(app, resolved_settings)
    return app


app = create_app()
