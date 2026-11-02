from pydantic import AwareDatetime
from .base import ApiModel


class LinkCodeData(ApiModel):
    code: str
    deep_link: str
    expires_at: AwareDatetime


class LinkStatusData(ApiModel):
    linked: bool
    linked_at: AwareDatetime | None = None
