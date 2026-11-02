from fastapi import APIRouter, Depends, Request
from ..schemas.base import Envelope
from ..schemas.reminders import ReminderEvent, ReminderEventData
from ..utils.internal_auth import require_internal_key
from ..utils.response import success

router = APIRouter(prefix='/internal/v1', tags=['Reminders'], dependencies=[Depends(require_internal_key)])


@router.post('/reminder-events', response_model=Envelope[ReminderEventData], operation_id='INT-06')
def reminder_event(body: ReminderEvent, request: Request) -> dict:
    """UC-17, UC-19: accepted giả, chưa persist/chưa gửi Telegram."""
    # TODO: logic thật theo UC-17/19: duplicate→stale→atomic event/state/job trước accepted.
    return success(request, ReminderEventData(result='accepted'))
