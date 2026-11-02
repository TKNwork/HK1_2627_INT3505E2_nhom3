from typing import Generic, TypeVar
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra='forbid')


T = TypeVar('T')


class Envelope(ApiModel, Generic[T]):
    request_id: str
    data: T


class HealthData(ApiModel):
    service: str
    status: str = 'ok'
    mode: str = 'stub'


def validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError('Timezone IANA không hợp lệ.') from exc
    return value


class ErrorDetail(ApiModel):
    field: str
    reason: str


class ErrorBody(ApiModel):
    code: str
    message: str
    details: list[ErrorDetail]


class ErrorEnvelope(ApiModel):
    request_id: str
    error: ErrorBody
