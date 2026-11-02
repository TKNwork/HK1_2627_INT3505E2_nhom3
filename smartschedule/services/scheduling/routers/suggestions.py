from fastapi import APIRouter, Depends, Request
from ..schemas.base import Envelope
from ..schemas.scheduling import SuggestionRequest, SuggestionData
from ..utils.internal_auth import require_internal_key
from ..utils.response import success

router = APIRouter(prefix='/internal/v1', tags=['Scheduling'], dependencies=[Depends(require_internal_key)])


@router.post('/suggestions', response_model=Envelope[SuggestionData], operation_id='INT-03')
def suggestions(body: SuggestionRequest, request: Request) -> dict:
    """UC-11: fixture, chưa tính lịch thật."""
    # TODO: logic thật theo UC-11; hiện không đọc DB hoặc chạy thuật toán.
    return success(request, SuggestionData(suggestions=[]))
