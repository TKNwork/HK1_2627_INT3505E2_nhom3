"""Tests for Scheduling INT-02 conflict detection.

Run from smartschedule/:
    pytest services/scheduling/tests/test_conflicts.py -q

Requires services.scheduling.services.conflict_service with:
    intervals_overlap(candidate, busy_slot)
    find_conflicts(candidate, busy_slots)
"""
from datetime import datetime, timezone
from types import SimpleNamespace

from services.scheduling.services.conflict_service import intervals_overlap, find_conflicts


def dt(hour, minute=0):
    return datetime(2026, 11, 7, hour, minute, tzinfo=timezone.utc)


def slot(start, end, task_id="task-1"):
    return SimpleNamespace(start_at=start, end_at=end, task_id=task_id)


def candidate(start, end, exclude_task_id=None):
    return SimpleNamespace(start_at=start, end_at=end, exclude_task_id=exclude_task_id)


def test_detects_intersection():
    assert intervals_overlap(candidate(dt(9), dt(10)), slot(dt(9, 30), dt(10, 30)))


def test_adjacent_intervals_do_not_conflict():
    assert not intervals_overlap(candidate(dt(9), dt(10)), slot(dt(10), dt(11)))


def test_candidate_inside_busy_slot_is_conflict():
    assert intervals_overlap(candidate(dt(9, 15), dt(9, 45)), slot(dt(9), dt(10)))


def test_busy_slot_inside_candidate_is_conflict():
    assert intervals_overlap(candidate(dt(9), dt(11)), slot(dt(9, 30), dt(10, 30)))


def test_returns_only_overlapping_slots():
    proposed = candidate(dt(9), dt(10))
    busy = [
        slot(dt(8), dt(9), "before"),
        slot(dt(9, 15), dt(9, 30), "overlap-1"),
        slot(dt(9, 45), dt(10, 15), "overlap-2"),
        slot(dt(10), dt(11), "after"),
    ]
    assert [x.task_id for x in find_conflicts(proposed, busy)] == ["overlap-1", "overlap-2"]


def test_excludes_task_being_rescheduled():
    proposed = candidate(dt(9), dt(10), exclude_task_id="current")
    busy = [slot(dt(9), dt(10), "current"), slot(dt(9, 30), dt(10, 30), "other")]
    assert [x.task_id for x in find_conflicts(proposed, busy)] == ["other"]


def test_returns_empty_list_when_there_is_no_conflict():
    proposed = candidate(dt(9), dt(10))
    busy = [slot(dt(7), dt(8), "earlier"), slot(dt(10), dt(11), "later")]
    assert find_conflicts(proposed, busy) == []


def test_sorts_conflicts_by_start_time():
    proposed = candidate(dt(9), dt(12))
    busy = [
        slot(dt(11), dt(11, 30), "later"),
        slot(dt(9, 30), dt(10), "earlier"),
        slot(dt(10, 30), dt(11), "middle"),
    ]
    assert [x.task_id for x in find_conflicts(proposed, busy)] == ["earlier", "middle", "later"]
