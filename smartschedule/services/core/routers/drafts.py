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
    """UC-09: tạo bản nháp từ yêu cầu tiếng Việt và trả 201."""
    draft = await create_from_text(body, user.id, repository, ai, get_request_id(request))
    return success(request, DraftData(draft=draft))


@router.get('/{id}', response_model=Envelope[DraftData], operation_id='API-10',
            responses={status: {'model': ErrorEnvelope} for status in (404, 410)})
def get_draft(id: str, request: Request, row=Depends(load_owned_draft)) -> dict:
    """Đọc bản nháp sau khi kiểm tra quyền sở hữu và hạn dùng."""
    return success(request, DraftData(draft=draft_response(row)))


@router.patch('/{id}', response_model=Envelope[DraftData], operation_id='API-11')
def patch_draft(id: str, body: PatchDraft, request: Request, row=Depends(load_owned_draft)) -> dict:
    """UC-10: còn trả dữ liệu mẫu, chưa cập nhật bản nháp."""
    # TODO: logic thật theo UC-10/11/17: fields, state, version; không gia hạn TTL.
    return success(request, DraftData(draft=stub_draft(id, version=2)))


@router.post('/{id}/suggestions', response_model=Envelope[SuggestionsData], operation_id='API-12')
def suggest(id: str, body: SuggestDraft, request: Request, row=Depends(load_owned_draft)) -> dict:
    """UC-11: còn trả gợi ý mẫu, chưa gọi Scheduling."""
    # TODO: logic thật theo UC-11: đủ đầu vào, đọc busy, Scheduling và cập nhật draft.
    return success(request, SuggestionsData(draft=stub_draft(id, version=2, with_suggestions=True),
                                           notice='STUB: gợi ý không giữ chỗ.'))


def require_idempotency_key(key: Annotated[str | None, Header(alias='Idempotency-Key')] = None) -> str:
    """Thiếu Idempotency-Key thì trả 400; chưa xử lý chống trùng."""
    if key is None or not key.strip():
        raise AppError(ErrorCode.IDEMPOTENCY_KEY_REQUIRED, 400, 'Yêu cầu header Idempotency-Key.')
    return key


@router.post('/{id}/confirm', status_code=201, response_model=Envelope[ConfirmData], operation_id='API-13')
def confirm(id: str, body: ExpectedVersion, request: Request,
            key: Annotated[str, Depends(require_idempotency_key)], row=Depends(load_owned_draft)) -> dict:
    """UC-12: còn trả dữ liệu mẫu, chưa tạo task hoặc chống trùng."""
    # TODO: logic thật theo UC-12: replay, TTL/version, kiểm trùng và transaction atomic.
    return success(request, ConfirmData(task=stub_task(), draft=stub_draft(id, version=2, confirmed=True)))
