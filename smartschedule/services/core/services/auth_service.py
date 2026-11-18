"""UC-01 (Đăng ký) và UC-02 (Đăng nhập) – business logic thật."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select, update
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

# Helpers

def _build_token_pair(user: Users, settings: Settings, db: Session, session_id: str) -> dict:
    """Tạo cặp token và đưa refresh token vào transaction hiện tại."""
    access_token, expires_at = create_access_token(user.id, settings)
    raw_refresh = generate_refresh_token()
    refresh_row = RefreshTokens(
        user_id=user.id,
        session_id=session_id,
        token_hash=hash_refresh_token(raw_refresh),
        expires_at=get_refresh_expiry(settings),
    )
    db.add(refresh_row)
    return {
        'access_token': access_token,
        'refresh_token': raw_refresh,
        'expires_in': settings.jwt_access_expire_minutes * 60,
        'expires_at': expires_at,
    }


# UC-01: Đăng ký

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


# UC-02: Đăng nhập

def login_user(email: str, password: str, settings: Settings, db: Session) -> dict:
    """Xác thực email + password, trả về user kèm cặp token.

    - Trả dict ``{'user': Users, **tokens}``.
    - Ném lỗi ``INVALID_CREDENTIALS`` nếu sai thông tin đăng nhập.
    """
    normalized_email = email.strip().lower()
    with db.begin():
        user = db.scalar(select(Users).where(Users.email == normalized_email))
        if user is None or not verify_password(password, user.password_hash):
            raise AppError(ErrorCode.INVALID_CREDENTIALS, 401, 'Email hoặc mật khẩu không đúng.')
        # The same lock orders token issuance, rotation, reuse and logout.
        user = db.scalar(select(Users).where(Users.id == user.id).with_for_update())
        if user is None:
            raise AppError(ErrorCode.INVALID_CREDENTIALS, 401, 'Email hoặc mật khẩu không đúng.')
        tokens = _build_token_pair(user, settings, db, str(uuid4()))
    return {'user': user, **tokens}


def _lock_refresh_user(db: Session, token_hash: str) -> Users | None:
    user_id = db.scalar(select(RefreshTokens.user_id).where(RefreshTokens.token_hash == token_hash))
    if user_id is None:
        return None
    return db.scalar(select(Users).where(Users.id == user_id).with_for_update())


def refresh_tokens(raw_refresh: str, settings: Settings, db: Session) -> dict:
    """Vô hiệu refresh token cũ và lưu token mới trong cùng transaction."""
    token_hash = hash_refresh_token(raw_refresh)
    with db.begin():
        user = _lock_refresh_user(db, token_hash)
        if user is None:
            raise AppError(ErrorCode.UNAUTHORIZED, 401, 'Refresh token không tồn tại.')
        row = db.scalar(select(RefreshTokens).where(RefreshTokens.token_hash == token_hash))
        if row is None:
            raise AppError(ErrorCode.UNAUTHORIZED, 401, 'Refresh token không tồn tại.')

        expires_at = row.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            raise AppError(ErrorCode.UNAUTHORIZED, 401, 'Refresh token đã hết hạn.')

        if row.revoked:
            # Dùng lại token đã thu hồi thì thu hồi mọi refresh token của user.
            db.execute(update(RefreshTokens).where(
                RefreshTokens.user_id == row.user_id,
                RefreshTokens.revoked.is_(False),
            ).values(revoked=True))
        else:
            row.revoked = True
            return _build_token_pair(user, settings, db, row.session_id)

    # Báo lỗi sau khi transaction đã commit việc thu hồi.
    raise AppError(ErrorCode.UNAUTHORIZED, 401, 'Refresh token đã bị thu hồi.')


# ---------------------------------------------------------------------------
# Logout (revoke refresh token)
# ---------------------------------------------------------------------------

def revoke_refresh_token(raw_refresh: str, db: Session) -> None:
    """Vô hiệu cả chuỗi refresh token của phiên đang đăng xuất."""
    token_hash = hash_refresh_token(raw_refresh)
    with db.begin():
        user = _lock_refresh_user(db, token_hash)
        if user is None:
            return
        row = db.scalar(select(RefreshTokens).where(RefreshTokens.token_hash == token_hash))
        if row is not None:
            db.execute(update(RefreshTokens).where(
                RefreshTokens.user_id == user.id,
                RefreshTokens.session_id == row.session_id,
                RefreshTokens.revoked.is_(False),
            ).values(revoked=True))
