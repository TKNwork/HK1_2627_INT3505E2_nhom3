from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request
from ..schemas.base import Envelope
from ..schemas.telegram import LinkCodeData, LinkCodeRequest, LinkStatusData
from ..utils.internal_auth import require_internal_key
from ..utils.response import success

router = APIRouter(prefix='/internal/v1/telegram', tags=['Telegram'], dependencies=[Depends(require_internal_key)])


@router.post('/link-codes', status_code=201, response_model=Envelope[LinkCodeData], operation_id='INT-04')
def link_code(body: LinkCodeRequest, request: Request) -> dict:
    """UC-14: mã fixture, không phải mã liên kết thật."""
    # TODO: logic thật theo UC-14: mã10 phút dùng1 lần, hash và Telegram adapter.
    return success(request, LinkCodeData(code='STUB-NOT-A-REAL-CODE',
        deep_link='https://t.me/SmartScheduleStubBot?start=STUB-NOT-A-REAL-CODE',
        expires_at=datetime(2030, 11, 1, 3, 10, tzinfo=timezone.utc)))


@router.get('/links/{userId}', response_model=Envelope[LinkStatusData], response_model_exclude_none=True,
            operation_id='INT-05')
def link_status(userId: str, request: Request) -> dict:
    """UC-14: trạng thái liên kết giả."""
    # TODO: logic thật theo UC-14: đọc mapping thuộc DB Notification.
    return success(request, LinkStatusData(linked=False))
