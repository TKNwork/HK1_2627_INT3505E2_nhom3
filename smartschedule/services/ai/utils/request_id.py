from uuid import uuid4
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


def get_request_id(request: Request) -> str:
    return getattr(request.state, 'request_id', None) or request.headers.get('X-Request-Id') or str(uuid4())


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.request_id = get_request_id(request)
        response = await call_next(request)
        response.headers['X-Request-Id'] = request.state.request_id
        return response
