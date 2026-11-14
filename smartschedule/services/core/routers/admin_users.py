from typing import Annotated
from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.admin_users import (
    AdminCreateUserRequest,
    AdminUpdateUserRequest,
    UserDetail,
    UserListResponse,
)
from ..schemas.base import Envelope
from ..services.admin_user_service import (
    create_user_by_admin,
    delete_user_by_admin,
    get_user_by_id,
    list_users,
    update_user_by_admin,
)
from ..utils.auth import CurrentUser, require_admin
from ..utils.response import success

router = APIRouter(prefix='/api/v1/admin/users', tags=['Admin - Users'])


@router.get('', response_model=Envelope[UserListResponse], operation_id='ADMIN-LIST-USERS')
def get_users_list(
    request: Request,
    current_admin: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    search: str | None = Query(None, description='Tìm kiếm theo email'),
    role: str | None = Query(None, pattern=r'^(user|admin)$', description='Lọc theo role'),
    limit: int = Query(50, ge=1, le=100, description='Số lượng tối đa'),
    offset: int = Query(0, ge=0, description='Vị trí bắt đầu'),
) -> dict:
    """Admin: Lấy danh sách tài khoản người dùng."""
    total, items = list_users(db, search=search, role=role, limit=limit, offset=offset)
    data = UserListResponse(
        total=total,
        items=[
            UserDetail(
                id=u.id,
                email=u.email,
                role=u.role,
                created_at=u.created_at,
                updated_at=u.updated_at,
            )
            for u in items
        ],
    )
    return success(request, data)


@router.post('', status_code=201, response_model=Envelope[UserDetail], operation_id='ADMIN-CREATE-USER')
def create_new_user(
    body: AdminCreateUserRequest,
    request: Request,
    current_admin: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Admin: Tạo tài khoản người dùng mới (chỉ định role 'user' hoặc 'admin')."""
    user = create_user_by_admin(email=body.email, password=body.password, role=body.role, db=db)
    return success(
        request,
        UserDetail(
            id=user.id,
            email=user.email,
            role=user.role,
            created_at=user.created_at,
            updated_at=user.updated_at,
        ),
    )


@router.get('/{user_id}', response_model=Envelope[UserDetail], operation_id='ADMIN-GET-USER')
def get_user_detail(
    user_id: str,
    request: Request,
    current_admin: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Admin: Xem chi tiết một tài khoản người dùng theo ID."""
    user = get_user_by_id(user_id, db)
    return success(
        request,
        UserDetail(
            id=user.id,
            email=user.email,
            role=user.role,
            created_at=user.created_at,
            updated_at=user.updated_at,
        ),
    )


@router.patch('/{user_id}', response_model=Envelope[UserDetail], operation_id='ADMIN-UPDATE-USER')
def update_user_info(
    user_id: str,
    body: AdminUpdateUserRequest,
    request: Request,
    current_admin: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Admin: Cập nhật thông tin tài khoản người dùng (email, role, hoặc đổi mật khẩu)."""
    user = update_user_by_admin(
        user_id=user_id,
        email=body.email,
        password=body.password,
        role=body.role,
        current_admin_id=current_admin.id,
        db=db,
    )
    return success(
        request,
        UserDetail(
            id=user.id,
            email=user.email,
            role=user.role,
            created_at=user.created_at,
            updated_at=user.updated_at,
        ),
    )


@router.delete('/{user_id}', status_code=204, operation_id='ADMIN-DELETE-USER')
def delete_user(
    user_id: str,
    request: Request,
    current_admin: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """Admin: Xóa tài khoản người dùng."""
    delete_user_by_admin(user_id=user_id, current_admin_id=current_admin.id, db=db)
    return Response(status_code=204, headers={'X-Request-Id': request.state.request_id if hasattr(request.state, 'request_id') else ''})

