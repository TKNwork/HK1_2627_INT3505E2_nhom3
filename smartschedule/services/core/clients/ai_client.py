"""Client HTTP để Core gọi API trích xuất nội bộ của AI service."""
from ..config import Settings
from ..utils.errors import ErrorCode
from .http_client import InternalClient


class AIClient(InternalClient):
    """Thiết lập địa chỉ, khóa nội bộ, timeout và mã lỗi riêng cho AI service."""
    def __init__(self, settings: Settings, **kwargs) -> None:
        """Nhận settings và tùy chọn transport; ánh xạ lỗi AI 502/503/504 theo contract."""
        super().__init__(settings.ai_base_url, settings.internal_api_key, settings.ai_timeout_seconds,
                         ErrorCode.AI_UNAVAILABLE, ErrorCode.AI_TIMEOUT, ErrorCode.AI_INVALID_RESPONSE,
                         error_statuses={502: ErrorCode.AI_INVALID_RESPONSE, 503: ErrorCode.AI_UNAVAILABLE,
                                         504: ErrorCode.AI_TIMEOUT}, **kwargs)

    async def extract(self, payload: dict, request_id: str) -> dict:
        """Gửi payload tới POST /internal/v1/extractions và trả phần data; Core kiểm schema nghiệp vụ."""
        return await self.request('POST', '/internal/v1/extractions', request_id, payload)
