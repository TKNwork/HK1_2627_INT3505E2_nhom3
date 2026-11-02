from ..config import Settings
from ..utils.errors import ErrorCode
from .http_client import InternalClient


class SchedulingClient(InternalClient):
    def __init__(self, settings: Settings, **kwargs) -> None:
        super().__init__(settings.scheduling_base_url, settings.internal_api_key, settings.scheduling_timeout_seconds,
                         ErrorCode.SCHEDULING_UNAVAILABLE, **kwargs)

    async def conflicts(self, payload: dict, request_id: str) -> dict:
        # TODO: typed DTO adapter when implementing the corresponding UC.
        return await self.request('POST', '/internal/v1/conflicts', request_id, payload)

    async def suggestions(self, payload: dict, request_id: str) -> dict:
        # TODO: typed DTO adapter when implementing the corresponding UC.
        return await self.request('POST', '/internal/v1/suggestions', request_id, payload)
