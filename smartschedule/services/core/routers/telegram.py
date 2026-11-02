from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request
from ..schemas.base import Envelope
from ..schemas.telegram import LinkCodeData, LinkStatusData
from ..utils.auth import get_current_user
from ..utils.response import success

router = APIRouter(prefix='/api/v1/telegram', tags=['Telegram'], dependencies=[Depends(get_current_user)])


@router.post('/link-codes', status_code=201, response_model=Envelope[LinkCodeData], operation_id='API-15')
def link_code(request: Request) -> dict:
    """UC-14: xin mã liên kết (stub, không dùng được với bot thật)."""
    # TODO: logic thật theo UC-14: gọi Notification client và truyền requestId.
    return success(request, LinkCodeData(code='STUB-NOT-A-REAL-CODE',
                   deep_link='https://t.me/SmartScheduleStubBot?start=STUB-NOT-A-REAL-CODE',
                   expires_at=datetime(2030, 11, 1, 3, 10, tzinfo=timezone.utc)))


@router.get('/link', response_model=Envelope[LinkStatusData], response_model_exclude_none=True,
            operation_id='API-16')
def link_status(request: Request) -> dict:
    """UC-14: trạng thái Telegram (stub)."""
    # TODO: logic thật theo UC-14: lấy userId từ JWT, gọi Notification.
    return success(request, LinkStatusData(linked=False))
