import httpx
from pydantic import ValidationError
from ..clients.llm_client import LLMClient
from ..config import Settings
from ..schemas.extractions import ExtractionRequest, Warning
from .extraction import extract_rules, normalize


async def extract_request(body: ExtractionRequest, settings: Settings, request_id: str):
    if settings.llm_api_key and settings.llm_base_url and settings.llm_model:
        try:
            fields = await LLMClient(settings).extract(body, request_id)
            return normalize(fields, body)
        except (httpx.HTTPError, ValidationError, ValueError, KeyError, IndexError, TypeError):
            result = extract_rules(body)
            result.warnings.append(Warning(code='LLM_FALLBACK',
                message='Không dùng được kết quả LLM; bản nháp được trích xuất bằng quy tắc.'))
            return result
    return extract_rules(body)
