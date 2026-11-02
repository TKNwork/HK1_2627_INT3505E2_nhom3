from datetime import date as Date
from typing import Annotated
from pydantic import AfterValidator, AwareDatetime, Field
from .base import ApiModel, validate_timezone

TimezoneName = Annotated[str, AfterValidator(validate_timezone)]


class ExtractionRequest(ApiModel):
    source_text: str = Field(min_length=1, max_length=2000)
    timezone: TimezoneName
    now: AwareDatetime


class ExtractionFields(ApiModel):
    title: str | None = None
    date: Date | None = None
    start_at: AwareDatetime | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)
    deadline_at: AwareDatetime | None = None
    timezone: TimezoneName | None = None
    reminder_minutes: int | None = None


class Warning(ApiModel):
    code: str
    message: str


class ExtractionData(ApiModel):
    fields: ExtractionFields
    missing_fields: list[str]
    required_input_fields: list[str]
    warnings: list[Warning]
