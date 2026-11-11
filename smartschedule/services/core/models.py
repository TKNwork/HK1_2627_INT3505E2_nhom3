"""SQLAlchemy models from docs/03.database.md; no business implementation."""
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from .database import Base

JsonType = JSON().with_variant(JSONB(), 'postgresql')

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def new_id() -> str:
    return str(uuid4())


class Users(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(128), nullable=False, primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class RefreshTokens(Base):
    """Refresh tokens stored in DB, valid for 7 days."""
    __tablename__ = 'refresh_tokens'
    id: Mapped[str] = mapped_column(String(128), nullable=False, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (
        Index('ix_refresh_tokens_user', 'user_id'),
        Index('ix_refresh_tokens_hash', 'token_hash'),
    )


class Tasks(Base):
    __tablename__ = 'tasks'
    id: Mapped[str] = mapped_column(String(128), nullable=False, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey('users.id'), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timezone: Mapped[str] = mapped_column(String(255), nullable=False)
    reminder_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'completed')", name="ck_tasks_status"),
        CheckConstraint('duration_minutes BETWEEN 1 AND 1440', name="ck_tasks_duration"),
        CheckConstraint('(start_at IS NULL AND end_at IS NULL) OR (start_at IS NOT NULL AND end_at IS NOT NULL)', name="ck_tasks_time_pair"),
        CheckConstraint('end_at IS NULL OR end_at > start_at', name="ck_tasks_time_order"),
        CheckConstraint('end_at IS NULL OR deadline_at IS NULL OR end_at <= deadline_at', name="ck_tasks_deadline"),
        CheckConstraint('reminder_minutes IS NULL OR reminder_minutes IN (5, 10, 15, 30)', name="ck_tasks_reminder"),
        CheckConstraint('version >= 1', name="ck_tasks_version"),
        CheckConstraint('char_length(btrim(title)) BETWEEN 1 AND 200', name="ck_tasks_title").ddl_if(dialect='postgresql'),
        CheckConstraint("end_at IS NULL OR end_at = start_at + duration_minutes * INTERVAL '1 minute'", name="ck_tasks_duration_matches").ddl_if(dialect='postgresql'),
        Index('ix_tasks_user_start', 'user_id', 'start_at'),
        Index('ix_tasks_user_created_id', 'user_id', 'created_at', 'id'),
    )

class ScheduleDrafts(Base):
    __tablename__ = 'schedule_drafts'
    id: Mapped[str] = mapped_column(String(128), nullable=False, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey('users.id'), nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    fields: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)
    missing_fields: Mapped[list[Any]] = mapped_column(JsonType, nullable=False, default=list)
    required_input_fields: Mapped[list[Any]] = mapped_column(JsonType, nullable=False, default=list)
    warnings: Mapped[list[Any]] = mapped_column(JsonType, nullable=False, default=list)
    suggestions: Mapped[list[Any]] = mapped_column(JsonType, nullable=False, default=list)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    confirmed_task_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    __table_args__ = (
        CheckConstraint("state IN ('needs_input', 'ready_to_schedule', 'ready_to_confirm', 'confirmed')", name="ck_schedule_drafts_state"),
    )

class IdempotencyRecords(Base):
    __tablename__ = 'idempotency_records'
    id: Mapped[str] = mapped_column(String(128), nullable=False, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey('users.id'), nullable=False)
    operation: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    response_data: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        UniqueConstraint('user_id', 'operation', 'idempotency_key', name='uq_idempotency_user_operation_key'),
    )

class OutboxEvents(Base):
    __tablename__ = 'outbox_events'
    event_id: Mapped[str] = mapped_column(String(128), nullable=False, primary_key=True, default=new_id)
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    task_id: Mapped[str] = mapped_column(String(128), nullable=False)
    task_version: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'processing', 'delivered')", name="ck_outbox_events_status"),
    )
