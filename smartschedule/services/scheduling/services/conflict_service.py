from collections.abc import Sequence

from ..schemas.scheduling import Candidate, BusySlot


def intervals_overlap(
    candidate: Candidate,
    busy_slot: BusySlot,
) -> bool:
    """
    Kiểm tra hai khoảng thời gian có giao nhau không.

    Sử dụng khoảng [startAt, endAt).
    Hai công việc nối tiếp nhau không bị tính là xung đột.
    """
    return (
        candidate.start_at < busy_slot.end_at
        and busy_slot.start_at < candidate.end_at
    )


def find_conflicts(
    candidate: Candidate,
    busy_slots: Sequence[BusySlot],
) -> list[BusySlot]:
    """Trả về toàn bộ task có lịch trùng với candidate."""

    conflicts = []

    for busy_slot in busy_slots:
        if (
            candidate.exclude_task_id is not None
            and busy_slot.task_id == candidate.exclude_task_id
        ):
            continue

        if intervals_overlap(candidate, busy_slot):
            conflicts.append(busy_slot)

    return sorted(
        conflicts,
        key=lambda slot: slot.start_at,
    )