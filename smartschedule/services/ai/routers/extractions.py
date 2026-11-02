from fastapi import APIRouter, Depends, Request
from ..schemas.base import Envelope
from ..schemas.extractions import ExtractionData, ExtractionFields, ExtractionRequest, Warning
from ..utils.internal_auth import require_internal_key
from ..utils.response import success

router = APIRouter(prefix='/internal/v1', tags=['Extraction'], dependencies=[Depends(require_internal_key)])


@router.post('/extractions', response_model=Envelope[ExtractionData], operation_id='INT-01')
def extract(body: ExtractionRequest, request: Request) -> dict:
    """UC-09: extraction fixture, không gọi LLM thật."""
    # TODO: logic thật theo UC-09: adapter LLM, schema, missing fields và lỗi provider.
    return success(request, ExtractionData(
        fields=ExtractionFields(title='Làm bài SOA (STUB)', date='2030-11-02',
                                duration_minutes=90, timezone='Asia/Ho_Chi_Minh'),
        missing_fields=['startAt'], required_input_fields=[],
        warnings=[Warning(code='STUB_RESPONSE', message='Dữ liệu giả, chưa gọi LLM.')]))
