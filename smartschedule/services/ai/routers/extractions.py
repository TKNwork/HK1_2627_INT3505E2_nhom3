"""API nội bộ nhận yêu cầu trích xuất, được bảo vệ bằng internal API key."""
from fastapi import APIRouter, Depends, Request
from ..schemas.base import Envelope
from ..schemas.extractions import ExtractionData, ExtractionRequest
from ..utils.internal_auth import require_internal_key
from ..utils.response import success

router = APIRouter(prefix='/internal/v1', tags=['Extraction'], dependencies=[Depends(require_internal_key)])


@router.post('/extractions', response_model=Envelope[ExtractionData], operation_id='INT-01')
async def extract(body: ExtractionRequest, request: Request) -> dict:
    """Chuyển request đã kiểm tra sang extract_request, giữ requestId và trả envelope 200."""
    from ..services.provider import extract_request
    from ..utils.request_id import get_request_id
    result = await extract_request(body, request.app.state.settings, get_request_id(request))
    return success(request, result)
