from pydantic import AwareDatetime, Field, model_validator
from .base import ApiModel


class Slot(ApiModel):
    start_at: AwareDatetime
    end_at: AwareDatetime

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.end_at <= self.start_at:
            raise ValueError("endAt phải lớn hơn startAt.")
        return self

class BusySlot(Slot):
    task_id: str


class Candidate(Slot):
    exclude_task_id: str | None = None


class ConflictRequest(ApiModel):
    candidate: Candidate
    busy: list[BusySlot]


class ConflictData(ApiModel):
    has_conflict: bool
    conflicts: list[BusySlot]


class SuggestionRequest(ApiModel):
    duration_minutes: int = Field(ge=1, le=1440, strict=True)
    search_from: AwareDatetime
    search_to: AwareDatetime
    deadline_at: AwareDatetime | None = None
    busy: list[BusySlot]
    max_results: int = Field(ge=1, le=3, strict=True)


class SuggestionData(ApiModel):
    suggestions: list[Slot]
