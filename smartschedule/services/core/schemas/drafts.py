from datetime import date as Date
from typing import Literal
from pydantic import AliasChoices, AwareDatetime, Field, field_validator
from .base import ApiModel
from .tasks import Duration, ReminderMinutes, TimezoneName, Title, Version, Task


class Warning(ApiModel):
    code: str
    message: str


class Slot(ApiModel):
    start_at: AwareDatetime
    end_at: AwareDatetime


class DraftFields(ApiModel):
    title: Title | None = None
    date: Date | None = None
    start_at: AwareDatetime | None = None
    duration_minutes: Duration | None = None
    deadline_at: AwareDatetime | None = None
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
    timezone: TimezoneName = 'Asia/Ho_Chi_Minh'
    reference_time: AwareDatetime | None = Field(default=None, validation_alias=AliasChoices('referenceTime', 'reference_time'))

    @field_validator('source_text')
    @classmethod
    def clean_text(cls, value: str) -> str:
        """Bỏ khoảng trắng hai đầu và từ chối nội dung trống."""
        if not value.strip():
            raise ValueError('Nội dung không được để trống.')
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
