import asyncio

import httpx
from ..clients.llm_client import LLMClient
from ..config import Settings
from ..schemas.extractions import ExtractionRequest, Warning
from ..utils.errors import AppError, ErrorCode
from .extraction import extract_rules, normalize


async def extract_request(body: ExtractionRequest, settings: Settings, request_id: str):
    """Ưu tiên LLM khi đủ cấu hình; khi lỗi thì dùng quy tắc kèm cảnh báo."""
    provider_error = None
    if settings.llm_api_key and settings.llm_base_url and settings.llm_model:
        try:
            async with asyncio.timeout(settings.llm_timeout_seconds):
                fields = await LLMClient(settings).extract(body, request_id)
            return normalize(fields, body)
        except (TimeoutError, httpx.TimeoutException):
            provider_error = AppError(ErrorCode.AI_TIMEOUT, 504, 'Provider quá thời gian phản hồi.')
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (408, 504):
                provider_error = AppError(ErrorCode.AI_TIMEOUT, 504, 'Provider quá thời gian phản hồi.')
            else:
                provider_error = AppError(ErrorCode.AI_UNAVAILABLE, 503, 'Provider không khả dụng.')
        except (httpx.HTTPError, httpx.InvalidURL):
            provider_error = AppError(ErrorCode.AI_UNAVAILABLE, 503, 'Provider không khả dụng.')
        except (ValueError, KeyError, IndexError, TypeError, OverflowError):
            provider_error = AppError(ErrorCode.AI_INVALID_RESPONSE, 502, 'Provider trả kết quả không hợp lệ.')

    try:
        result = extract_rules(body)
    except (ValueError, OverflowError) as exc:
        raise (provider_error or AppError(
            ErrorCode.AI_INVALID_RESPONSE, 502, 'Không thể chuẩn hóa kết quả trích xuất.',
        )) from exc
    if provider_error:
        result.warnings.append(Warning(code='LLM_FALLBACK',
            message='Không dùng được kết quả LLM; bản nháp được trích xuất bằng quy tắc.'))
    return result
