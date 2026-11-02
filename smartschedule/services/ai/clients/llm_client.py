from ..config import Settings


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def extract(self, source_text: str, timezone: str, now: str, request_id: str) -> dict:
        # TODO UC-09: httpx adapter provider, timeout, kiểm schema và truyền requestId.
        raise NotImplementedError('LLM integration is intentionally absent.')
