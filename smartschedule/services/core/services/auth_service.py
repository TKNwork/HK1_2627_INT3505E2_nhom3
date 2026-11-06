"""UC-01 (Đăng ký) và UC-02 (Đăng nhập) – business logic thật."""
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import Settings
from ..models import RefreshTokens, Users
from ..utils.auth import (
    create_access_token,
    generate_refresh_token,
    get_refresh_expiry,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from ..utils.errors import AppError, ErrorCode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_token_pair(user: Users, settings: Settings, db: Session) -> dict:
    """Tạo cặp access + refresh token, lưu refresh vào DB."""
    access_token, expires_at = create_access_token(user.id, settings)
    raw_refresh = generate_refresh_token()
    refresh_row = RefreshTokens(
        user_id=user.id,
        token_hash=hash_refresh_token(raw_refresh),
        expires_at=get_refresh_expiry(settings),
    )
    db.add(refresh_row)
    db.commit()
    return {
        'access_token': access_token,
        'refresh_token': raw_refresh,
        'expires_in': settings.jwt_access_expire_minutes * 60,
        'expires_at': expires_at,
    }


# ---------------------------------------------------------------------------
# UC-01: Đăng ký
# ---------------------------------------------------------------------------

def register_user(email: str, password: str, db: Session) -> Users:
    """Tạo tài khoản mới.

    - Chuẩn hóa email (trim + lowercase).
    - Băm mật khẩu bằng Argon2id.
    - Trả về entity ``Users`` đã lưu.
    - Ném lỗi ``EMAIL_ALREADY_EXISTS`` nếu email trùng.
    """
    normalized_email = email.strip().lower()
    user = Users(
        email=normalized_email,
        password_hash=hash_password(password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(ErrorCode.EMAIL_ALREADY_EXISTS, 409, 'Email đã được sử dụng.')
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# UC-02: Đăng nhập
# ---------------------------------------------------------------------------

def login_user(email: str, password: str, settings: Settings, db: Session) -> dict:
    """Xác thực email + password, trả về user kèm cặp token.

    - Trả dict ``{'user': Users, **tokens}``.
    - Ném lỗi ``INVALID_CREDENTIALS`` nếu sai thông tin đăng nhập.
    """
    normalized_email = email.strip().lower()
    user = db.query(Users).filter(Users.email == normalized_email).first()
    if user is None or not verify_password(password, user.password_hash):
        raise AppError(ErrorCode.INVALID_CREDENTIALS, 401, 'Email hoặc mật khẩu không đúng.')
    tokens = _build_token_pair(user, settings, db)
    return {'user': user, **tokens}


# ---------------------------------------------------------------------------
# Refresh token
# ---------------------------------------------------------------------------

def refresh_tokens(raw_refresh: str, settings: Settings, db: Session) -> dict:
    """Xoay refresh token (rotation): vô hiệu token cũ, trả cặp mới.

    - Ném lỗi ``UNAUTHORIZED`` nếu token không hợp lệ / hết hạn / đã revoke.
    """
    token_hash = hash_refresh_token(raw_refresh)
    row = db.query(RefreshTokens).filter(RefreshTokens.token_hash == token_hash).first()

    if row is None:
        raise AppError(ErrorCode.UNAUTHORIZED, 401, 'Refresh token không tồn tại.')
    if row.revoked:
        # Token đã bị revoke → có thể bị đánh cắp, revoke tất cả token của user
        db.query(RefreshTokens).filter(
            RefreshTokens.user_id == row.user_id,
            RefreshTokens.revoked == False,  # noqa: E712
        ).update({'revoked': True})
        db.commit()
        raise AppError(ErrorCode.UNAUTHORIZED, 401, 'Refresh token đã bị thu hồi.')

    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise AppError(ErrorCode.UNAUTHORIZED, 401, 'Refresh token đã hết hạn.')

    # Revoke token cũ
    row.revoked = True
    db.commit()

    # Lấy user để tạo cặp mới
    user = db.query(Users).filter(Users.id == row.user_id).first()
    if user is None:
        raise AppError(ErrorCode.UNAUTHORIZED, 401, 'Tài khoản không tồn tại.')

    tokens = _build_token_pair(user, settings, db)
    return tokens


# ---------------------------------------------------------------------------
# Logout (revoke refresh token)
# ---------------------------------------------------------------------------

def revoke_refresh_token(raw_refresh: str, db: Session) -> None:
    """Vô hiệu một refresh token (dùng khi logout)."""
    token_hash = hash_refresh_token(raw_refresh)
    row = db.query(RefreshTokens).filter(RefreshTokens.token_hash == token_hash).first()
    if row and not row.revoked:
        row.revoked = True
        db.commit()
