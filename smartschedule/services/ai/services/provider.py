"""Chọn LLM hoặc bộ quy tắc cho một yêu cầu trích xuất."""
import httpx
from pydantic import ValidationError
from ..clients.llm_client import LLMClient
from ..config import Settings
from ..schemas.extractions import ExtractionRequest, Warning
from .extraction import extract_rules, normalize


async def extract_request(body: ExtractionRequest, settings: Settings, request_id: str):
    """Trích xuất từ LLM khi đủ cấu hình, nếu không thì dùng extract_rules.

    Lỗi provider hoặc dữ liệu LLM không hợp lệ trong các trường hợp được bắt sẽ
    chuyển sang bộ quy tắc và thêm cảnh báo LLM_FALLBACK. Khi chưa cấu hình LLM,
    dùng quy tắc trực tiếp mà không thêm cảnh báo này. Kết quả trả là ExtractionData;
    lỗi ngoài các trường hợp đã bắt vẫn được truyền lên."""
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
