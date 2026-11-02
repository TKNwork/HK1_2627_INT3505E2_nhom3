from fastapi import APIRouter, Depends, Request
from ..schemas.base import Envelope
from ..schemas.scheduling import ConflictRequest, ConflictData
from ..utils.internal_auth import require_internal_key
from ..utils.response import success

router = APIRouter(prefix='/internal/v1', tags=['Scheduling'], dependencies=[Depends(require_internal_key)])


@router.post('/conflicts', response_model=Envelope[ConflictData], operation_id='INT-02')
def conflicts(body: ConflictRequest, request: Request) -> dict:
    """UC-03, UC-06, UC-12: fixture, chưa tính lịch thật."""
    # TODO: logic thật theo UC-03, UC-06, UC-12; hiện không đọc DB hoặc chạy thuật toán.
    return success(request, ConflictData(has_conflict=False, conflicts=[]))
