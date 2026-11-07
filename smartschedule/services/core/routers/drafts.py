"""Các API bản nháp; UC-09 và GET đã xử lý thật, các UC tiếp theo còn trả mẫu."""
from typing import Annotated
from fastapi import APIRouter, Depends, Header, Request
from ..schemas.base import Envelope, ErrorEnvelope
from ..schemas.drafts import ConfirmData, CreateDraft, DraftData, PatchDraft, SuggestDraft, SuggestionsData
from ..schemas.tasks import ExpectedVersion
from ..services.fixtures import stub_draft, stub_task
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
    """Nhận POST đã kiểm tra đầu vào, gọi create_from_text và trả bản nháp trong envelope 201."""
    draft = await create_from_text(body, user.id, repository, ai, get_request_id(request))
    return success(request, DraftData(draft=draft))


@router.get('/{id}', response_model=Envelope[DraftData], operation_id='API-10',
            responses={status: {'model': ErrorEnvelope} for status in (404, 410)})
def get_draft(id: str, request: Request, row=Depends(load_owned_draft)) -> dict:
    """Trả bản nháp đã lưu sau khi load_owned_draft kiểm tra chủ sở hữu và TTL."""
    return success(request, DraftData(draft=draft_response(row)))


@router.patch('/{id}', response_model=Envelope[DraftData], operation_id='API-11')
def patch_draft(id: str, body: PatchDraft, request: Request, row=Depends(load_owned_draft)) -> dict:
    """Khung UC-10/11/17: kiểm quyền và TTL, trả dữ liệu mẫu; chưa cập nhật DB."""
    # TODO: logic thật theo UC-10/11/17: fields, state, version; không gia hạn TTL.
    return success(request, DraftData(draft=stub_draft(id, version=2)))


@router.post('/{id}/suggestions', response_model=Envelope[SuggestionsData], operation_id='API-12')
def suggest(id: str, body: SuggestDraft, request: Request, row=Depends(load_owned_draft)) -> dict:
    """Khung UC-11: kiểm quyền và TTL, trả gợi ý mẫu; chưa gọi Scheduling hoặc giữ chỗ."""
    # TODO: logic thật theo UC-11: đủ đầu vào, đọc busy, Scheduling và cập nhật draft.
    return success(request, SuggestionsData(draft=stub_draft(id, version=2, with_suggestions=True),
                                           notice='STUB: gợi ý không giữ chỗ.'))


def require_idempotency_key(key: Annotated[str | None, Header(alias='Idempotency-Key')] = None) -> str:
    """Bắt buộc header Idempotency-Key không rỗng; thiếu trả 400, chưa kiểm tra trùng request."""
    if key is None or not key.strip():
        raise AppError(ErrorCode.IDEMPOTENCY_KEY_REQUIRED, 400, 'Yêu cầu header Idempotency-Key.')
    return key


@router.post('/{id}/confirm', status_code=201, response_model=Envelope[ConfirmData], operation_id='API-13')
def confirm(id: str, body: ExpectedVersion, request: Request,
            key: Annotated[str, Depends(require_idempotency_key)], row=Depends(load_owned_draft)) -> dict:
    """Khung UC-12: kiểm header, quyền và TTL rồi trả mẫu; chưa tạo task hoặc lưu kết quả chống trùng."""
    # TODO: logic thật theo UC-12: replay, TTL/version, kiểm trùng và transaction atomic.
    return success(request, ConfirmData(task=stub_task(), draft=stub_draft(id, version=2, confirmed=True)))
