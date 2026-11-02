from typing import Any
from fastapi import Request
from starlette.responses import JSONResponse
from .request_id import get_request_id


def success(request: Request, data: Any) -> dict[str, Any]:
    return {'requestId': get_request_id(request), 'data': data}


def failure(request: Request, code: str, status: int, message: str,
            details: list[dict[str, str]] | None = None) -> JSONResponse:
    request_id = get_request_id(request)
    return JSONResponse(status_code=status, content={
        'requestId': request_id,
        'error': {'code': code, 'message': message, 'details': details or []},
    }, headers={'X-Request-Id': request_id})
