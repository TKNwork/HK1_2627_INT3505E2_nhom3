from datetime import datetime, timedelta, timezone
from typing import Annotated
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Users
from ..config import Settings
from ..schemas.base import ApiModel
from .errors import AppError, ErrorCode

bearer = HTTPBearer(auto_error=False)
hasher = PasswordHasher()


class CurrentUser(ApiModel):
    id: str


def hash_password(password: str) -> str:
    return hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_access_token(user_id: str, settings: Settings) -> tuple[str, datetime]:
    settings.require_auth_secrets()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.jwt_expire_minutes)
    token = jwt.encode({'sub': user_id, 'iat': now, 'exp': expires_at}, settings.jwt_secret, algorithm='HS256')
    return token, expires_at


def decode_access_token(token: str, settings: Settings) -> CurrentUser:
    """Xác minh JWT HS256 và lấy user ID từ sub; token sai hoặc hết hạn trả 401."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=['HS256'],
                             options={'require': ['sub', 'iat', 'exp']})
        if not isinstance(payload['sub'], str) or not payload['sub']:
            raise jwt.InvalidTokenError('Missing subject')
        return CurrentUser(id=payload['sub'])
    except jwt.InvalidTokenError as exc:
        raise AppError(ErrorCode.UNAUTHORIZED, 401, 'Token không hợp lệ hoặc đã hết hạn.') from exc


def get_current_user(request: Request,
                     credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
                     session: Annotated[Session, Depends(get_db)]) -> CurrentUser:
    """Đọc Bearer JWT và kiểm tra tài khoản còn tồn tại trong DB Core."""
    if credentials is None or credentials.scheme.lower() != 'bearer':
        raise AppError(ErrorCode.UNAUTHORIZED, 401, 'Yêu cầu JWT Bearer.')
    user = decode_access_token(credentials.credentials, request.app.state.settings)
    if session.get(Users, user.id) is None:
        raise AppError(ErrorCode.UNAUTHORIZED, 401, 'Tài khoản không tồn tại.')
    return user
