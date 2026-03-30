from __future__ import annotations

import logging
import redis as redis_lib
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.app.api.v1 import api_router
from backend.app.core.config import Settings, get_settings
from backend.app.core.database import init_database
from backend.app.core.logging import configure_logging
from backend.app.core.rate_limit import create_limiter
from backend.app.dependencies import get_app_settings
from backend.app.middleware.request_id import RequestIdMiddleware
from backend.app.models import load_model_modules

logger = logging.getLogger(__name__)


def _validate_startup_config(settings: Settings) -> None:
    """Validate critical settings at startup. Warns in dev, raises in production."""
    if not settings.feishu_encryption_key:
        msg = 'FEISHU_ENCRYPTION_KEY is not set — feishu app_secret encryption will not work.'
        if settings.environment == 'production':
            raise RuntimeError(msg)
        logger.warning(msg)


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


def validate_startup_config(settings: Settings) -> None:
    """Refuse to start in production when critical secrets are using placeholder defaults.

    Rules (per D-12, D-05):
    - environment == 'production' + jwt_secret_key == 'change_me'  → RuntimeError (hard fail)
    - environment == 'production' + public_api_key == 'your_public_api_key'  → RuntimeError (hard fail)
    - environment == 'production' + Redis unreachable  → RuntimeError (hard fail, per D-05)
    - deepseek_api_key == 'your_deepseek_api_key' (any environment) → loud WARNING only (soft fail)
    """
    if settings.environment == 'production':
        errors: list[str] = []
        if settings.jwt_secret_key == 'change_me':
            errors.append(
                'JWT_SECRET_KEY is set to the default placeholder "change_me". '
                'Generate a secure random key: python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )
        if settings.public_api_key == 'your_public_api_key':
            errors.append(
                'PUBLIC_API_KEY is set to the default placeholder "your_public_api_key". '
                'Set a strong random value in your .env file.'
            )
        # D-05: production must have reachable Redis (rate limiting enforcement depends on it)
        try:
            redis_lib.from_url(settings.redis_url).ping()
        except Exception:
            errors.append(
                f'Redis is unreachable at {settings.redis_url!r} in production — '
                'cannot enforce rate limits. Start Redis and verify REDIS_URL in .env.'
            )
        if errors:
            error_text = '\n'.join(f'  - {e}' for e in errors)
            raise RuntimeError(
                f'Production startup blocked — insecure configuration detected:\n{error_text}'
            )
    if settings.deepseek_api_key == 'your_deepseek_api_key':
        logger.warning(
            'DEEPSEEK_API_KEY is set to the placeholder value. '
            'AI evaluations will use fallback stub responses. '
            'Set a real API key for production use.'
        )


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    configure_logging(settings)
    validate_startup_config(settings)
    load_model_modules()
    init_database()
    _validate_startup_config(settings)

    # Feishu scheduler (optional - only if config exists)
    try:
        from backend.app.scheduler.feishu_scheduler import start_scheduler, stop_scheduler as _stop_scheduler
        from backend.app.models.feishu_config import FeishuConfig
        from backend.app.core.database import SessionLocal
        _sched_db = SessionLocal()
        try:
            _config = _sched_db.query(FeishuConfig).filter(FeishuConfig.is_active.is_(True)).first()
            if _config:
                start_scheduler(_config.sync_hour, _config.sync_minute, _config.sync_timezone)
            else:
                logger.info('No active Feishu config found, scheduler not started')
        finally:
            _sched_db.close()
    except Exception:
        logger.warning('Failed to start Feishu scheduler, attendance sync disabled', exc_info=True)

    logger.info('Starting %s v%s', settings.app_name, settings.app_version)
    yield

    # Stop feishu scheduler
    try:
        from backend.app.scheduler.feishu_scheduler import stop_scheduler
        stop_scheduler()
    except Exception:
        pass

    logger.info('Stopping %s', settings.app_name)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        # If detail is already a dict (e.g. duplicate_file error), return it directly
        if isinstance(exc.detail, dict):
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
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
    app.add_middleware(RequestIdMiddleware)


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
    app_limiter = create_limiter(resolved_settings)
    app.state.limiter = app_limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    register_middlewares(app, resolved_settings)
    register_exception_handlers(app)
    register_routes(app, resolved_settings)
    return app


app = create_app()
