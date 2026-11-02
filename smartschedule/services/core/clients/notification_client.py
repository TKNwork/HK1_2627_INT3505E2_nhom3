from ..config import Settings
from ..utils.errors import ErrorCode
from .http_client import InternalClient


class NotificationClient(InternalClient):
    def __init__(self, settings: Settings, **kwargs) -> None:
        super().__init__(settings.notification_base_url, settings.internal_api_key, settings.notification_timeout_seconds,
                         ErrorCode.NOTIFICATION_UNAVAILABLE, **kwargs)

    async def link_code(self, payload: dict, request_id: str) -> dict:
        # TODO: typed DTO adapter when implementing the corresponding UC.
        return await self.request('POST', '/internal/v1/telegram/link-codes', request_id, payload)

    async def reminder_event(self, payload: dict, request_id: str) -> dict:
        # TODO: typed DTO adapter when implementing the corresponding UC.
        return await self.request('POST', '/internal/v1/reminder-events', request_id, payload)

    async def link_status(self, user_id: str, request_id: str) -> dict:
        from urllib.parse import quote
        return await self.request('GET', '/internal/v1/telegram/links/' + quote(user_id, safe=''), request_id)
