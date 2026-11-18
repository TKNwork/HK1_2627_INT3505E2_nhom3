from typing import Annotated
from fastapi import APIRouter, Depends, Header, Request
from ..schemas.base import Envelope, ErrorEnvelope
from ..schemas.drafts import ConfirmData, CreateDraft, DraftData, PatchDraft, SuggestDraft, SuggestionsData
from ..schemas.tasks import ExpectedVersion
from ..utils.auth import CurrentUser, get_current_user
from ..services.drafts import create_from_text, draft_response, get_ai_client, get_draft_repository, load_owned_draft
from ..utils.request_id import get_request_id
from ..utils.errors import AppError, ErrorCode
from ..utils.response import success

router = APIRouter(prefix='/api/v1/schedule-drafts', tags=['Drafts'], dependencies=[Depends(get_current_user)])


@router.post('', status_code=201, response_model=Envelope[DraftData], operation_id='API-09',
             responses={status: {'model': ErrorEnvelope} for status in (502, 503, 504)})
async def create_draft(body: CreateDraft, request: Request,
                       user: CurrentUser = Depends(get_current_user),
                       repository=Depends(get_draft_repository), ai=Depends(get_ai_client)) -> dict:
    """UC-09: tạo bản nháp từ yêu cầu tiếng Việt và trả 201."""
    draft = await create_from_text(body, user.id, repository, ai, get_request_id(request))
    return success(request, DraftData(draft=draft))


@router.get('/{id}', response_model=Envelope[DraftData], operation_id='API-10',
            responses={status: {'model': ErrorEnvelope} for status in (404, 410)})
def get_draft(id: str, request: Request, row=Depends(load_owned_draft)) -> dict:
    """Đọc bản nháp sau khi kiểm tra quyền sở hữu và hạn dùng."""
    return success(request, DraftData(draft=draft_response(row)))


def check_draft_version(row, expected_version: int) -> None:
    if row.state == 'confirmed':
        raise AppError(ErrorCode.DRAFT_ALREADY_CONFIRMED, 409, 'Bản nháp đã được xác nhận.')
    if row.version != expected_version:
        raise AppError(ErrorCode.VERSION_CONFLICT, 409, 'Phiên bản bản nháp đã thay đổi.')


@router.patch('/{id}', response_model=Envelope[DraftData], operation_id='API-11',
              responses=dict.fromkeys((404, 409, 410, 501), {'model': ErrorEnvelope}))
def patch_draft(id: str, body: PatchDraft, request: Request, row=Depends(load_owned_draft)) -> dict:
    check_draft_version(row, body.expected_version)
    raise AppError(ErrorCode.NOT_IMPLEMENTED, 501, 'Chỉnh sửa bản nháp chưa được triển khai.')


@router.post('/{id}/suggestions', response_model=Envelope[SuggestionsData], operation_id='API-12',
             responses=dict.fromkeys((404, 409, 410, 422, 501, 503), {'model': ErrorEnvelope}))
def suggest(id: str, body: SuggestDraft, request: Request, row=Depends(load_owned_draft)) -> dict:
    check_draft_version(row, body.expected_version)
    if row.state == 'needs_input':
        raise AppError(ErrorCode.DRAFT_NOT_READY, 422, 'Bản nháp chưa đủ đầu vào để tìm giờ.')
    raise AppError(ErrorCode.NOT_IMPLEMENTED, 501, 'Gợi ý lịch chưa được triển khai.')


def require_idempotency_key(key: Annotated[str | None, Header(alias='Idempotency-Key')] = None) -> str:
    """Thiếu Idempotency-Key thì trả 400; chưa xử lý chống trùng."""
    if key is None or not key.strip():
        raise AppError(ErrorCode.IDEMPOTENCY_KEY_REQUIRED, 400, 'Yêu cầu header Idempotency-Key.')
    return key


@router.post('/{id}/confirm', status_code=201, response_model=Envelope[ConfirmData], operation_id='API-13',
             responses=dict.fromkeys((404, 409, 410, 422, 501, 503), {'model': ErrorEnvelope}))
def confirm(id: str, body: ExpectedVersion, request: Request,
            key: Annotated[str, Depends(require_idempotency_key)], row=Depends(load_owned_draft)) -> dict:
    check_draft_version(row, body.expected_version)
    if row.state != 'ready_to_confirm':
        raise AppError(ErrorCode.DRAFT_NOT_READY, 422, 'Bản nháp chưa thể xác nhận.')
    raise AppError(ErrorCode.NOT_IMPLEMENTED, 501, 'Xác nhận bản nháp chưa được triển khai.')
