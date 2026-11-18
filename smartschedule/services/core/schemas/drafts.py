import re
from datetime import date as Date, datetime
from typing import Annotated, Literal
from pydantic import AliasChoices, AwareDatetime, BeforeValidator, Field, field_validator
from .base import ApiModel
from .tasks import Duration, ReminderMinutes, TimezoneName, Title, Version, Task


def validate_rfc3339(value):
    if isinstance(value, datetime) or isinstance(value, str) and re.fullmatch(
        r'[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt][0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:[Zz]|[+-][0-9]{2}:[0-9]{2})',
        value,
    ):
        return value
    raise ValueError('Thời gian phải theo RFC3339 và có offset.')


RFC3339 = Annotated[AwareDatetime, BeforeValidator(validate_rfc3339)]


class Warning(ApiModel):
    code: str
    message: str


class Slot(ApiModel):
    start_at: AwareDatetime
    end_at: AwareDatetime


class DraftFields(ApiModel):
    title: Title | None = None
    date: Date | None = None
    start_at: RFC3339 | None = None
    duration_minutes: Duration | None = None
    deadline_at: RFC3339 | None = None
    timezone: TimezoneName | None = None
    reminder_minutes: ReminderMinutes | None = None


class ExtractionResult(ApiModel):
    fields: DraftFields
    missing_fields: list[str]
    required_input_fields: list[str]
    warnings: list[Warning]


class Draft(ApiModel):
    id: str
    source_text: str
    fields: DraftFields
    missing_fields: list[str]
    required_input_fields: list[str]
    warnings: list[Warning]
    suggestions: list[Slot]
    state: Literal['needs_input', 'ready_to_schedule', 'ready_to_confirm', 'confirmed']
    version: Version
    confirmed_task_id: str | None
    expires_at: AwareDatetime


class CreateDraft(ApiModel):
    source_text: str = Field(min_length=1, max_length=2000, validation_alias=AliasChoices('sourceText', 'source_text', 'text', 'prompt'))
    timezone: TimezoneName
    reference_time: RFC3339 | None = Field(default=None, validation_alias=AliasChoices('referenceTime', 'reference_time'))

    @field_validator('source_text')
    @classmethod
    def clean_text(cls, value: str) -> str:
        """Bỏ khoảng trắng hai đầu và từ chối nội dung trống."""
        if not value.strip():
            raise ValueError('Nội dung không được để trống.')
        if '\x00' in value:
            raise ValueError('Nội dung chứa ký tự không hợp lệ.')
        return value.strip()


class PatchDraft(ApiModel):
    expected_version: Version
    fields: DraftFields


class SuggestDraft(ApiModel):
    expected_version: Version
    search_from: AwareDatetime | None = None
    search_to: AwareDatetime | None = None
    max_results: int = Field(default=3, ge=1, le=3)


class DraftData(ApiModel):
    draft: Draft


class SuggestionsData(DraftData):
    notice: str


class ConfirmData(DraftData):
    task: Task
