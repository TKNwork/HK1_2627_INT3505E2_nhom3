from typing import Annotated, Literal
from pydantic import AfterValidator, AwareDatetime, Field, model_validator
from .base import ApiModel, validate_timezone


class Reminder(ApiModel):
    title: str = Field(min_length=1, max_length=200)
    start_at: AwareDatetime
    timezone: Annotated[str, AfterValidator(validate_timezone)]
    reminder_minutes: Literal[5, 10, 15, 30]


class ReminderEvent(ApiModel):
    event_id: str
    event_type: str
    task_id: str
    task_version: int = Field(ge=1, strict=True)
    user_id: str
    action: Literal['upsert', 'cancel']
    reminder: Reminder | None = None

    @model_validator(mode='after')
    def require_reminder_for_upsert(self) -> 'ReminderEvent':
        if self.action == 'upsert' and self.reminder is None:
            raise ValueError('reminder bắt buộc khi action=upsert.')
        return self


class ReminderEventData(ApiModel):
    result: Literal['accepted', 'duplicate', 'ignored_stale']
