from datetime import date
from pydantic import AwareDatetime
from .base import ApiModel
from .tasks import Task, TimezoneName


class CalendarData(ApiModel):
    date: date
    timezone: TimezoneName
    range_start: AwareDatetime
    range_end: AwareDatetime
    items: list[Task]
