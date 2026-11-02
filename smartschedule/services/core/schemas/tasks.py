from typing import Annotated, Literal
from pydantic import AfterValidator, AwareDatetime, Field
from .base import ApiModel, validate_timezone

Duration = Annotated[int, Field(strict=True, ge=1, le=1440)]
Version = Annotated[int, Field(strict=True, ge=1)]
ReminderMinutes = Literal[5, 10, 15, 30]
TimezoneName = Annotated[str, AfterValidator(validate_timezone)]
Title = Annotated[str, Field(min_length=1, max_length=200)]


class Task(ApiModel):
    id: str
    title: Title
    status: Literal['pending', 'completed']
    start_at: AwareDatetime | None
    end_at: AwareDatetime | None
    duration_minutes: Duration
    deadline_at: AwareDatetime | None
    timezone: TimezoneName
    reminder_minutes: ReminderMinutes | None
    version: Version
    created_at: AwareDatetime
    updated_at: AwareDatetime


class CreateTask(ApiModel):
    title: Title
    duration_minutes: Duration
    timezone: TimezoneName
    start_at: AwareDatetime | None = None
    deadline_at: AwareDatetime | None = None
    reminder_minutes: ReminderMinutes | None = None


class PatchTask(ApiModel):
    expected_version: Version
    title: Title | None = None
    start_at: AwareDatetime | None = None
    duration_minutes: Duration | None = None
    deadline_at: AwareDatetime | None = None
    reminder_minutes: ReminderMinutes | None = None
    timezone: TimezoneName | None = None
    # TODO UC-06: phân biệt omitted với explicit null bằng model_fields_set.


class ExpectedVersion(ApiModel):
    expected_version: Version


class TaskData(ApiModel):
    task: Task


class TaskListData(ApiModel):
    items: list[Task]
    next_cursor: str | None
