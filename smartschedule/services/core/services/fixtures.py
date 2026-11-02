"""Static skeleton fixtures. They do not persist or implement scheduling rules."""
from datetime import datetime, timezone
from ..schemas.tasks import Task
from ..schemas.drafts import Draft, DraftFields, Slot

TZ = 'Asia/Ho_Chi_Minh'
SOURCE_TEXT = 'Ngày mai làm bài SOA trong 90 phút, xong trước 17 giờ'


def stub_slot() -> Slot:
    return Slot(start_at=datetime(2030, 11, 2, 3, tzinfo=timezone.utc),
                end_at=datetime(2030, 11, 2, 4, 30, tzinfo=timezone.utc))


def stub_task(task_id: str = 'task-stub', version: int = 1, completed: bool = False) -> Task:
    slot = stub_slot()
    return Task(id=task_id, title='Làm bài SOA (STUB)', status='completed' if completed else 'pending',
                start_at=slot.start_at, end_at=slot.end_at, duration_minutes=90,
                deadline_at=datetime(2030, 11, 2, 10, tzinfo=timezone.utc), timezone=TZ,
                reminder_minutes=15, version=version,
                created_at=datetime(2030, 11, 1, tzinfo=timezone.utc),
                updated_at=datetime(2030, 11, 1, tzinfo=timezone.utc))


def stub_draft(draft_id: str = 'draft-stub', version: int = 1, confirmed: bool = False,
               with_suggestions: bool = False) -> Draft:
    slot = stub_slot()
    return Draft(id=draft_id, source_text=SOURCE_TEXT,
                 fields=DraftFields(title='Làm bài SOA (STUB)', date='2030-11-02',
                                    duration_minutes=90, timezone=TZ,
                                    start_at=slot.start_at if confirmed else None),
                 missing_fields=[] if confirmed else ['startAt'], required_input_fields=[], warnings=[],
                 suggestions=[slot] if with_suggestions else [],
                 state='confirmed' if confirmed else 'ready_to_schedule', version=version,
                 confirmed_task_id='task-stub' if confirmed else None,
                 expires_at=datetime(2030, 11, 1, 3, 30, tzinfo=timezone.utc))
