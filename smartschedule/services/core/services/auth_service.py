"""UC-01 (Đăng ký tài khoản) – business logic."""
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import Users
from ..utils.auth import hash_password
from ..utils.errors import AppError, ErrorCode


def register_user(email: str, password: str, db: Session) -> Users:
    """Tạo tài khoản mới (UC-01).

    - Chuẩn hóa email (trim + lowercase).
    - Băm mật khẩu bằng Argon2id.
    - Lưu user vào cơ sở dữ liệu.
    - Ném lỗi EMAIL_ALREADY_EXISTS (409) nếu email đã tồn tại.
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
