import re
from datetime import date as Date, datetime
from typing import Annotated, Literal
from pydantic import AfterValidator, AliasChoices, AwareDatetime, BeforeValidator, Field, field_validator
from .base import ApiModel, validate_timezone

TimezoneName = Annotated[str, AfterValidator(validate_timezone)]


def validate_rfc3339(value):
    if isinstance(value, datetime) or isinstance(value, str) and re.fullmatch(
        r'[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt][0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:[Zz]|[+-][0-9]{2}:[0-9]{2})',
        value,
    ):
        return value
    raise ValueError('Thời gian phải theo RFC3339 và có offset.')


RFC3339 = Annotated[AwareDatetime, BeforeValidator(validate_rfc3339)]


class ExtractionRequest(ApiModel):
    source_text: str = Field(min_length=1, max_length=2000, validation_alias=AliasChoices('sourceText', 'source_text', 'text', 'prompt'))
    timezone: TimezoneName
    now: RFC3339 = Field(validation_alias=AliasChoices('now', 'referenceTime', 'reference_time'))

    @field_validator('source_text')
    @classmethod
    def clean_text(cls, value: str) -> str:
        """Bỏ khoảng trắng hai đầu và từ chối nội dung trống."""
        if not value.strip():
            raise ValueError('Nội dung không được để trống.')
        if '\x00' in value:
            raise ValueError('Nội dung chứa ký tự không hợp lệ.')
        return value.strip()


class ExtractionFields(ApiModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    date: Date | None = None
    start_at: RFC3339 | None = None
    duration_minutes: int | None = Field(default=None, strict=True, ge=1, le=1440)
    deadline_at: RFC3339 | None = None
    timezone: TimezoneName | None = None
    reminder_minutes: Literal[5, 10, 15, 30] | None = None

    @field_validator('title')
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is not None and '\x00' in value:
            raise ValueError('Tiêu đề chứa ký tự không hợp lệ.')
        return value


class Warning(ApiModel):
    code: str
    message: str


class ExtractionData(ApiModel):
    fields: ExtractionFields
    missing_fields: list[str]
    required_input_fields: list[str]
    warnings: list[Warning]
