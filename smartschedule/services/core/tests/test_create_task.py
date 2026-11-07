"""Tests for Core UC-03 task-creation helpers.

Run from smartschedule/:
    pytest services/core/tests/test_create_task.py -q

Requires services.core.services.task_creation with:
    calculate_end_at(body)
    build_conflict_payload(candidate, busy_tasks)
    build_reminder_event(task)
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from services.core.schemas.tasks import CreateTask
from services.core.services.task_creation import (
    calculate_end_at,
    build_conflict_payload,
    build_reminder_event,
)

UTC = timezone.utc


def make_body(**overrides):
    values = {
        "title": "Ôn tập CSDL",
        "duration_minutes": 60,
        "timezone": "Asia/Ho_Chi_Minh",
        "start_at": datetime(2026, 11, 7, 9, 0, tzinfo=UTC),
        "deadline_at": datetime(2026, 11, 7, 12, 0, tzinfo=UTC),
        "reminder_minutes": 10,
    }
    values.update(overrides)
    return CreateTask(**values)


def test_calculates_end_at_from_start_and_duration():
    body = make_body(duration_minutes=90)
    assert calculate_end_at(body) == body.start_at + timedelta(minutes=90)


def test_end_at_is_none_for_task_without_start_time():
    assert calculate_end_at(make_body(start_at=None)) is None


def test_builds_conflict_payload_in_camel_case():
    start = datetime(2026, 11, 7, 9, 0, tzinfo=UTC)
    end = datetime(2026, 11, 7, 10, 0, tzinfo=UTC)
    busy_start = datetime(2026, 11, 7, 9, 30, tzinfo=UTC)
    busy_end = datetime(2026, 11, 7, 10, 30, tzinfo=UTC)

    payload = build_conflict_payload(
        candidate=SimpleNamespace(start_at=start, end_at=end),
        busy_tasks=[SimpleNamespace(
            id="busy-1", start_at=busy_start, end_at=busy_end
        )],
    )

    assert payload == {
        "candidate": {"startAt": start.isoformat(), "endAt": end.isoformat()},
        "busy": [{
            "taskId": "busy-1",
            "startAt": busy_start.isoformat(),
            "endAt": busy_end.isoformat(),
        }],
    }


def test_conflict_payload_supports_empty_busy_list():
    start, end = datetime(2026, 11, 7, 9, tzinfo=UTC), datetime(2026, 11, 7, 10, tzinfo=UTC)
    payload = build_conflict_payload(
        candidate=SimpleNamespace(start_at=start, end_at=end),
        busy_tasks=[],
    )
    assert payload["busy"] == []


def test_builds_reminder_upsert_event():
    start = datetime(2026, 11, 7, 9, 0, tzinfo=UTC)
    task = SimpleNamespace(
        id="task-123", user_id="user-456", title="Ôn tập CSDL",
        start_at=start, end_at=start + timedelta(minutes=60),
        timezone="Asia/Ho_Chi_Minh", reminder_minutes=10, version=1,
    )

    event = build_reminder_event(task)

    assert event["event_type"] == "reminder_changed"
    assert event["task_id"] == "task-123"
    assert event["task_version"] == 1
    assert event["user_id"] == "user-456"
    assert event["action"] == "upsert"
    assert event["reminder"] == {
        "title": "Ôn tập CSDL",
        "start_at": start.isoformat(),
        "timezone": "Asia/Ho_Chi_Minh",
        "reminder_minutes": 10,
    }


@pytest.mark.parametrize("duration", [0, -1, 1441])
def test_rejects_duration_outside_allowed_range(duration):
    with pytest.raises(ValueError):
        make_body(duration_minutes=duration)


@pytest.mark.parametrize("minutes", [1, 20, 60])
def test_rejects_unsupported_reminder_interval(minutes):
    with pytest.raises(ValueError):
        make_body(reminder_minutes=minutes)


@pytest.mark.parametrize("minutes", [5, 10, 15, 30])
def test_accepts_supported_reminder_intervals(minutes):
    assert make_body(reminder_minutes=minutes).reminder_minutes == minutes
