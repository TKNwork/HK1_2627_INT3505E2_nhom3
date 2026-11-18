from datetime import date as Date
from typing import Annotated
from pydantic import AfterValidator, AliasChoices, AwareDatetime, Field, field_validator
from .base import ApiModel, validate_timezone

TimezoneName = Annotated[str, AfterValidator(validate_timezone)]


class ExtractionRequest(ApiModel):
    source_text: str = Field(min_length=1, max_length=2000, validation_alias=AliasChoices('sourceText', 'source_text', 'text', 'prompt'))
    timezone: TimezoneName = 'Asia/Ho_Chi_Minh'
    now: AwareDatetime = Field(validation_alias=AliasChoices('now', 'referenceTime', 'reference_time'))

    @field_validator('source_text')
    @classmethod
    def clean_text(cls, value: str) -> str:
        """Bỏ khoảng trắng hai đầu và từ chối nội dung trống."""
        if not value.strip():
            raise ValueError('Nội dung không được để trống.')
        return value.strip()


class ExtractionFields(ApiModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    date: Date | None = None
    start_at: AwareDatetime | None = None
    duration_minutes: int | None = Field(default=None, strict=True, ge=1, le=1440)
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
