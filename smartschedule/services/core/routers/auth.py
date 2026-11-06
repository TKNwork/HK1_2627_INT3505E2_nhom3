from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.auth import Credentials, LoginData, RegisterData, User
from ..schemas.base import Envelope
from ..services.auth_service import register_user
from ..utils.auth import create_access_token
from ..utils.response import success

router = APIRouter(prefix='/api/v1/auth', tags=['Auth'])


@router.post('/register', status_code=201, response_model=Envelope[RegisterData], operation_id='API-01')
def register(body: Credentials, request: Request, db: Session = Depends(get_db)) -> dict:
    """UC-01: Đăng ký tài khoản.

    1. Chuẩn hóa email và kiểm tra trùng lặp tại DB.
    2. Hash mật khẩu an toàn với Argon2id.
    3. Lưu tài khoản mới vào database.
    4. Trả thông tin user (chuyển sang đăng nhập).
    """
    user = register_user(body.email, body.password, db)
    return success(request, RegisterData(user=User(id=user.id, email=user.email)))


@router.post('/login', response_model=Envelope[LoginData], operation_id='API-02')
def login(body: Credentials, request: Request) -> dict:
    """UC-02: login fixture stub."""
    token, expiry = create_access_token('user-stub', request.app.state.settings)
    return success(request, LoginData(user=User(id='user-stub', email=body.email),
                                      access_token=token, expires_at=expiry))
