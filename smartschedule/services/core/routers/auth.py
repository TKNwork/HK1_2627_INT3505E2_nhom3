from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.auth import (
    Credentials,
    LoginData,
    RefreshData,
    RefreshRequest,
    RegisterData,
    User,
)
from ..schemas.base import Envelope
from ..services.auth_service import login_user, refresh_tokens, register_user, revoke_refresh_token
from ..utils.response import success

router = APIRouter(prefix='/api/v1/auth', tags=['Auth'])


@router.post('/register', status_code=201, response_model=Envelope[RegisterData], operation_id='API-01')
def register(body: Credentials, request: Request, db: Session = Depends(get_db)) -> dict:
    """UC-01: Đăng ký tài khoản.

    1. Kiểm tra email unique.
    2. Hash mật khẩu (Argon2id).
    3. Lưu user vào DB.
    4. Trả thông tin user (chuyển sang đăng nhập).
    """
    user = register_user(body.email, body.password, db)
    return success(request, RegisterData(user=User(id=user.id, email=user.email, role=user.role)))


@router.post('/login', response_model=Envelope[LoginData], operation_id='API-02')
def login(body: Credentials, request: Request, db: Session = Depends(get_db)) -> dict:
    """UC-02: Đăng nhập.

    1. Xác thực email + password.
    2. Tạo access token (JWT, 10 phút) → client lưu localStorage.
    3. Tạo refresh token (random, 7 ngày) → lưu hash vào DB.
    4. Trả cặp token cho client.
    """
    settings = request.app.state.settings
    result = login_user(body.email, body.password, settings, db)
    user = result['user']
    return success(request, LoginData(
        user=User(id=user.id, email=user.email, role=user.role),
        access_token=result['access_token'],
        refresh_token=result['refresh_token'],
        expires_in=result['expires_in'],
        expires_at=result['expires_at'],
    ))


@router.post('/refresh', response_model=Envelope[RefreshData], operation_id='AUTH-REFRESH')
def refresh(body: RefreshRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    """Đổi refresh token cũ lấy cặp token mới (rotation).

    - Refresh token cũ bị vô hiệu ngay sau khi dùng.
    - Nếu token đã bị revoke → revoke tất cả token của user (phòng đánh cắp).
    """
    settings = request.app.state.settings
    tokens = refresh_tokens(body.refresh_token, settings, db)
    return success(request, RefreshData(
        access_token=tokens['access_token'],
        refresh_token=tokens['refresh_token'],
        expires_in=tokens['expires_in'],
        expires_at=tokens['expires_at'],
    ))


@router.post('/logout', status_code=204, operation_id='AUTH-LOGOUT')
def logout(body: RefreshRequest, db: Session = Depends(get_db)) -> None:
    """Đăng xuất – vô hiệu refresh token."""
    revoke_refresh_token(body.refresh_token, db)
    return None
