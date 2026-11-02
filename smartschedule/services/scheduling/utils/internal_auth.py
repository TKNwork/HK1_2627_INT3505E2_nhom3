import secrets
from typing import Annotated
from fastapi import Header, Request
from .errors import AppError, ErrorCode


def require_internal_key(request: Request,
                         key: Annotated[str | None, Header(alias='X-Internal-Api-Key')] = None) -> None:
    expected = request.app.state.settings.internal_api_key
    if not key or not secrets.compare_digest(key, expected):
        raise AppError(ErrorCode.UNAUTHORIZED, 401, 'Khóa nội bộ không hợp lệ.')
