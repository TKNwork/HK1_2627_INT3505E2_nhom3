
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..models import Tasks, OutboxEvents, new_id
from ..schemas.tasks import CreateTask, Task
from ..clients.scheduling_client import SchedulingClient
from ..utils.errors import AppError, ErrorCode

def calculate_end_at(body: CreateTask):
    """Tính giờ kết thúc; task không có startAt thì endAt cũng None."""
    if body.start_at is None:
        return None

    return body.start_at + timedelta(minutes=body.duration_minutes)


def build_conflict_payload(candidate, busy_tasks):
    """Đổi dữ liệu Core sang định dạng request của Scheduling."""
    return {
        "candidate": {
            "startAt": candidate.start_at.isoformat(),
            "endAt": candidate.end_at.isoformat(),
        },
        "busy": [
            {
                "taskId": task.id,
                "startAt": task.start_at.isoformat(),
                "endAt": task.end_at.isoformat(),
            }
            for task in busy_tasks
        ],
    }

async def check_schedule_conflict(
    body: CreateTask,
    scheduling_client: SchedulingClient,
    request_id: str,
) -> None:
    """Gửi candidate và lịch bận sang Scheduling để kiểm tra."""
    
    candidate = SimpleNamespace(
        start_at=body.start_at,
        end_at=end_at,
    )

    payload = build_conflict_payload(candidate, busy_tasks)
    result = await scheduling_client.conflicts(payload, request_id)

    # Validate schema response từ Scheduling service
    if (
        not isinstance(result, dict)
        or "hasConflict" not in result
        or "conflicts" not in result
        or not isinstance(result["hasConflict"], bool)
        or not isinstance(result["conflicts"], list)
    ):
        raise AppError(
            ErrorCode.INTERNAL_SERVER_ERROR,
            500,
            "Phản hồi từ dịch vụ Lịch trình (Scheduling) không hợp lệ.",
        )

    if result["hasConflict"]:
        raise AppError(
            ErrorCode.SCHEDULE_CONFLICT,
            409,
            "Thời gian công việc bị trùng với lịch hiện có.",
            [
                {
                    "field": "startAt",
                    "reason": "Khoảng thời gian đã chọn có xung đột.",
                    "conflicts": result["conflicts"],  # Đưa danh sách xung đột vào chi tiết lỗi nếu cần
                }
            ],
        )



def build_task_response(task: Tasks) -> Task:
    """Chuyển SQLAlchemy Tasks thành DTO trả về API."""
    return Task(
        id=task.id,
        title=task.title,
        status=task.status,
        start_at=task.start_at,
        end_at=task.end_at,
        duration_minutes=task.duration_minutes,
        deadline_at=task.deadline_at,
        timezone=task.timezone,
        reminder_minutes=task.reminder_minutes,
        version=task.version,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def build_reminder_event(task: Tasks) -> dict:
    """Tạo payload theo schema ReminderEvent của Notification."""
    return {
        "event_id": new_id(),
        "event_type": "reminder_changed",
        "task_id": task.id,
        "task_version": task.version,
        "user_id": task.user_id,
        "action": "upsert",
        "reminder": {
            "title": task.title,
            "startAt": task.start_at.isoformat(),
            "timezone": task.timezone,
            "reminderMinutes": task.reminder_minutes,
        },
    }


async def create_manual_task(
    body: CreateTask,
    user_id: str,
    session: Session,
    scheduling_client: SchedulingClient,
    request_id: str,
) -> Task:
    """
    UC-03: kiểm tra lịch, lưu task và outbox trong cùng transaction.
    """

    end_at = calculate_end_at(body)

    if (
        end_at is not None
        and body.deadline_at is not None
        and end_at > body.deadline_at
    ):
        raise AppError(
            ErrorCode.DEADLINE_EXCEEDED,
            422,
            "Thời gian kết thúc vượt quá deadline.",
            [{"field": "deadlineAt", "reason": "Deadline phải sau hoặc bằng endAt."}],
        )

    now = datetime.now(timezone.utc)

    async with session.begin():
        await session.execute(
            text(
                """
                SELECT pg_advisory_xact_lock(
                    hashtextextended(:user_id, 0)
                )
                """
            ),
            {"user_id": str(user_id)},
        )


            busy_tasks = session.scalars(
                select(Tasks).where(
                    Tasks.user_id == user_id,
                    Tasks.start_at.is_not(None),
                    Tasks.end_at.is_not(None),
                    Tasks.start_at < end_at,
                    Tasks.end_at > body.start_at,
                )
            ).all()

            await check_schedule_conflict(
                body,
                end_at,
                busy_tasks,
                scheduling_client,
                request_id,
            )

        task = Tasks(
            user_id=user_id,
            title=body.title,
            status="pending",
            start_at=body.start_at,
            end_at=end_at,
            duration_minutes=body.duration_minutes,
            deadline_at=body.deadline_at,
            timezone=body.timezone,
            reminder_minutes=body.reminder_minutes,
            version=1,
            created_at=now,
            updated_at=now,
        )

        session.add(task)
        session.flush()

        # Chỉ tạo reminder event nếu task đã có lịch và được bật nhắc.
        if task.start_at is not None and task.reminder_minutes is not None:
            event = build_reminder_event(task)

            session.add(
                OutboxEvents(
                    event_id=event["event_id"],
                    event_type=event["event_type"],
                    task_id=task.id,
                    task_version=task.version,
                    payload=event,
                    status="pending",
                    attempt_count=0,
                    next_attempt_at=now,
                    created_at=now,
                )
            )

        session.flush()
        result = build_task_response(task)

    return result
