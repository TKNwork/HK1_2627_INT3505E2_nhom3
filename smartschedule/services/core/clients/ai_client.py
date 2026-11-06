from ..config import Settings
from ..utils.errors import ErrorCode
from .http_client import InternalClient


class AIClient(InternalClient):
    def __init__(self, settings: Settings, **kwargs) -> None:
        super().__init__(settings.ai_base_url, settings.internal_api_key, settings.ai_timeout_seconds,
                         ErrorCode.AI_UNAVAILABLE, ErrorCode.AI_TIMEOUT, ErrorCode.AI_INVALID_RESPONSE,
                         error_statuses={502: ErrorCode.AI_INVALID_RESPONSE, 503: ErrorCode.AI_UNAVAILABLE,
                                         504: ErrorCode.AI_TIMEOUT}, **kwargs)

    async def extract(self, payload: dict, request_id: str) -> dict:
        return await self.request('POST', '/internal/v1/extractions', request_id, payload)
