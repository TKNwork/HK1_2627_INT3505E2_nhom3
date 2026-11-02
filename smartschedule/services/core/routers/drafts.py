from typing import Annotated
from fastapi import APIRouter, Depends, Header, Request
from ..schemas.base import Envelope
from ..schemas.drafts import ConfirmData, CreateDraft, DraftData, PatchDraft, SuggestDraft, SuggestionsData
from ..schemas.tasks import ExpectedVersion
from ..services.fixtures import stub_draft, stub_task
from ..utils.auth import get_current_user
from ..utils.errors import AppError, ErrorCode
from ..utils.response import success

router = APIRouter(prefix='/api/v1/schedule-drafts', tags=['Drafts'], dependencies=[Depends(get_current_user)])


@router.post('', status_code=201, response_model=Envelope[DraftData], operation_id='API-09')
def create_draft(body: CreateDraft, request: Request) -> dict:
    """UC-09: extraction và tạo draft (stub)."""
    # TODO: logic thật theo UC-09: AI client, validate output và lưu draft TTL30 phút.
    return success(request, DraftData(draft=stub_draft()))


@router.get('/{id}', response_model=Envelope[DraftData], operation_id='API-10')
def get_draft(id: str, request: Request) -> dict:
    """UC-10: xem draft (stub)."""
    # TODO: logic thật theo UC-10: ownership/TTL và DRAFT_EXPIRED.
    return success(request, DraftData(draft=stub_draft(id)))


@router.patch('/{id}', response_model=Envelope[DraftData], operation_id='API-11')
def patch_draft(id: str, body: PatchDraft, request: Request) -> dict:
    """UC-10, UC-11, UC-17: sửa draft/chọn giờ/mức nhắc (stub)."""
    # TODO: logic thật theo UC-10/11/17: fields, state, version; không gia hạn TTL.
    return success(request, DraftData(draft=stub_draft(id, version=2)))


@router.post('/{id}/suggestions', response_model=Envelope[SuggestionsData], operation_id='API-12')
def suggest(id: str, body: SuggestDraft, request: Request) -> dict:
    """UC-11: tìm gợi ý không giữ chỗ (stub)."""
    # TODO: logic thật theo UC-11: đủ đầu vào, đọc busy, Scheduling và cập nhật draft.
    return success(request, SuggestionsData(draft=stub_draft(id, version=2, with_suggestions=True),
                                           notice='STUB: gợi ý không giữ chỗ.'))


def require_idempotency_key(key: Annotated[str | None, Header(alias='Idempotency-Key')] = None) -> str:
    if key is None or not key.strip():
        raise AppError(ErrorCode.IDEMPOTENCY_KEY_REQUIRED, 400, 'Yêu cầu header Idempotency-Key.')
    return key


@router.post('/{id}/confirm', status_code=201, response_model=Envelope[ConfirmData], operation_id='API-13')
def confirm(id: str, body: ExpectedVersion, request: Request,
            key: Annotated[str, Depends(require_idempotency_key)]) -> dict:
    """UC-12: confirm (stub); chỉ kiểm tra header, chưa idempotency thật."""
    # TODO: logic thật theo UC-12: replay, TTL/version, kiểm trùng và transaction atomic.
    return success(request, ConfirmData(task=stub_task(), draft=stub_draft(id, version=2, confirmed=True)))
