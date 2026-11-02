from datetime import date as Date, datetime, timezone as UtcTimezone
from typing import Annotated
from fastapi import APIRouter, Depends, Query, Request
from ..schemas.base import Envelope
from ..schemas.calendar import CalendarData
from ..schemas.tasks import TimezoneName
from ..services.fixtures import stub_task
from ..utils.auth import get_current_user
from ..utils.response import success

router = APIRouter(prefix='/api/v1/calendar', tags=['Calendar'], dependencies=[Depends(get_current_user)])


@router.get('', response_model=Envelope[CalendarData], operation_id='API-14')
def calendar(request: Request, date: Annotated[Date, Query()], timezone: Annotated[TimezoneName, Query()]) -> dict:
    """UC-13: lịch ngày (fixture cố định, chưa tính biên ngày thật)."""
    # TODO: logic thật theo UC-13: timezone/day range, giao khoảng và sắp theo startAt.
    return success(request, CalendarData(date=Date(2030, 11, 2), timezone='Asia/Ho_Chi_Minh',
                   range_start=datetime(2030, 11, 1, 17, tzinfo=UtcTimezone.utc),
                   range_end=datetime(2030, 11, 2, 17, tzinfo=UtcTimezone.utc), items=[stub_task()]))
