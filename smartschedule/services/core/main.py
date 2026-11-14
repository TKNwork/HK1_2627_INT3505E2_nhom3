from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from starlette.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from .config import Settings
from .schemas.base import Envelope, ErrorEnvelope, HealthData
from .utils.errors import AppError, ErrorCode
from .utils.request_id import RequestIdMiddleware
from .utils.response import failure, success
from .routers import auth, tasks, drafts, calendar, telegram, admin_users

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, *, init_database_on_startup: bool = True) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings.require_auth_secrets()
        if settings.init_db and init_database_on_startup:
            from .database import init_database
            init_database(settings)
        yield

    app = FastAPI(title=f'SmartSchedule {settings.service_name} — STUB', version='0.1.0', lifespan=lifespan,
                  responses={400: {'model': ErrorEnvelope}, 401: {'model': ErrorEnvelope},
                             500: {'model': ErrorEnvelope}})
    app.state.settings = settings
    app.add_middleware(RequestIdMiddleware)

    @app.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError) -> JSONResponse:
        return failure(request, exc.code, exc.http_status, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [{'field': '.'.join(str(part) for part in item['loc']), 'reason': item['msg']}
                   for item in exc.errors()]
        return failure(request, ErrorCode.VALIDATION_ERROR, 400, 'Dữ liệu không hợp lệ.', details)

    @app.exception_handler(StarletteHTTPException)
    async def framework_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        # Framework routing errors keep their HTTP status and the common error envelope.
        return failure(request, ErrorCode.VALIDATION_ERROR, exc.status_code, str(exc.detail))

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error('Unhandled exception: %s', type(exc).__name__)
        return failure(request, ErrorCode.INTERNAL_ERROR, 500, 'Lỗi nội bộ hệ thống.')

    @app.get('/health', response_model=Envelope[HealthData], tags=['Health'])
    def health(request: Request) -> dict:
        return success(request, HealthData(service=settings.service_name))

    app.include_router(auth.router)
    app.include_router(tasks.router)
    app.include_router(drafts.router)
    app.include_router(calendar.router)
    app.include_router(telegram.router)
    app.include_router(admin_users.router)
    def custom_openapi() -> dict:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
        for methods in schema['paths'].values():
            for operation in methods.values():
                if not isinstance(operation, dict) or 'responses' not in operation:
                    continue
                responses = operation['responses']
                # Validation is normalized to400; remove FastAPI's automatic422 schema.
                if 'HTTPValidationError' in str(responses.get('422', {})):
                    responses.pop('422')
                op = operation.get('operationId')
                if op in ('API-03', 'API-06', 'API-12', 'API-13'):
                    responses['422'] = {'description': 'Lỗi nghiệp vụ (chưa triển khai trong skeleton)',
                        'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ErrorEnvelope'}}}}
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi
    return app


app = create_app()
