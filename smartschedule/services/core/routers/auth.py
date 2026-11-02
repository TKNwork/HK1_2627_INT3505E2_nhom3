from fastapi import APIRouter, Request
from ..schemas.auth import Credentials, LoginData, RegisterData, User
from ..schemas.base import Envelope
from ..utils.auth import create_access_token
from ..utils.response import success

router = APIRouter(prefix='/api/v1/auth', tags=['Auth'])


@router.post('/register', status_code=201, response_model=Envelope[RegisterData], operation_id='API-01')
def register(body: Credentials, request: Request) -> dict:
    """UC-01: đăng ký (stub, không ghi DB)."""
    # TODO: logic thật theo UC-01: unique email, hash mật khẩu và lưu tài khoản.
    return success(request, RegisterData(user=User(id='user-stub', email=body.email.strip().lower())))


@router.post('/login', response_model=Envelope[LoginData], operation_id='API-02')
def login(body: Credentials, request: Request) -> dict:
    """UC-02: login fixture; chưa kiểm tra mật khẩu hoặc tài khoản."""
    # TODO: logic thật theo UC-02: đọc user và verify_password trước cấp JWT.
    token, expiry = create_access_token('user-stub', request.app.state.settings)
    return success(request, LoginData(user=User(id='user-stub', email=body.email),
                                      access_token=token, expires_at=expiry))
