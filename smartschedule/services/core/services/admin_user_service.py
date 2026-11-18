"""Business logic cho Admin quản trị tài khoản người dùng (RBAC User CRUD)."""
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import (
    IdempotencyRecords,
    RefreshTokens,
    ScheduleDrafts,
    Tasks,
    Users,
)
from ..utils.auth import hash_password
from ..utils.errors import AppError, ErrorCode


def list_users(
    db: Session,
    search: str | None = None,
    role: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[int, list[Users]]:
    """Lấy danh sách người dùng có phân trang và bộ lọc tìm kiếm."""
    query = db.query(Users)
    if search:
        search_pattern = f"%{search.strip().lower()}%"
        query = query.filter(Users.email.ilike(search_pattern))
    if role:
        query = query.filter(Users.role == role)

    total = query.with_entities(func.count(Users.id)).scalar() or 0
    items = query.order_by(Users.created_at.desc()).offset(offset).limit(limit).all()
    return total, items


def get_user_by_id(user_id: str, db: Session) -> Users:
    """Lấy thông tin chi tiết của một người dùng theo ID."""
    user = db.get(Users, user_id)
    if user is None:
        raise AppError(ErrorCode.USER_NOT_FOUND, 404, 'Không tìm thấy người dùng.')
    return user


def create_user_by_admin(email: str, password: str, role: str, db: Session) -> Users:
    """Admin tạo tài khoản mới (hỗ trợ chỉ định role 'user' hoặc 'admin')."""
    normalized_email = email.strip().lower()
    existing = db.query(Users).filter(Users.email == normalized_email).first()
    if existing:
        raise AppError(ErrorCode.EMAIL_ALREADY_EXISTS, 409, 'Email đã được sử dụng.')

    user = Users(
        email=normalized_email,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(ErrorCode.EMAIL_ALREADY_EXISTS, 409, 'Email đã được sử dụng.')
    db.refresh(user)
    return user


def update_user_by_admin(
    user_id: str,
    email: str | None,
    password: str | None,
    role: str | None,
    current_admin_id: str,
    db: Session,
) -> Users:
    """Admin cập nhật thông tin tài khoản người dùng."""
    user = get_user_by_id(user_id, db)

    # Nếu admin tự sửa role của chính mình thành không phải admin -> cần đảm bảo còn ít nhất 1 admin khác
    if role and role != 'admin' and user_id == current_admin_id:
        other_admin = db.query(Users).filter(Users.role == 'admin', Users.id != current_admin_id).first()
        if not other_admin:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                400,
                'Không thể hạ quyền tài khoản admin duy nhất trong hệ thống.',
            )

    if email is not None:
        normalized_email = email.strip().lower()
        if normalized_email != user.email:
            existing = db.query(Users).filter(Users.email == normalized_email, Users.id != user_id).first()
            if existing:
                raise AppError(ErrorCode.EMAIL_ALREADY_EXISTS, 409, 'Email đã được sử dụng.')
            user.email = normalized_email

    if password is not None:
        user.password_hash = hash_password(password)

    if role is not None:
        user.role = role

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(ErrorCode.EMAIL_ALREADY_EXISTS, 409, 'Email đã được sử dụng.')

    db.refresh(user)
    return user


def delete_user_by_admin(user_id: str, current_admin_id: str, db: Session) -> None:
    """Admin xóa tài khoản người dùng và dọn dẹp các dữ liệu liên quan."""
    if user_id == current_admin_id:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            400,
            'Không thể tự xóa tài khoản admin của chính mình.',
        )

    user = get_user_by_id(user_id, db)

    # Xóa các liên kết dữ liệu của user
    for model_cls in (RefreshTokens, Tasks, ScheduleDrafts, IdempotencyRecords):
        try:
            db.query(model_cls).filter(model_cls.user_id == user_id).delete(synchronize_session=False)
        except Exception:
            db.rollback()

    db.delete(user)
    db.commit()
