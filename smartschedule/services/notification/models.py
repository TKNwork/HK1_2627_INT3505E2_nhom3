"""SQLAlchemy models from docs/03.database.md; no business implementation."""
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from .database import Base

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def new_id() -> str:
    return str(uuid4())


class TelegramLinks(Base):
    __tablename__ = 'telegram_links'
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, primary_key=True)
    chat_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class TelegramLinkCodes(Base):
    __tablename__ = 'telegram_link_codes'
    id: Mapped[str] = mapped_column(String(128), nullable=False, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

class ReminderEvents(Base):
    __tablename__ = 'reminder_events'
    event_id: Mapped[str] = mapped_column(String(128), nullable=False, primary_key=True, default=new_id)
    task_id: Mapped[str] = mapped_column(String(128), nullable=False)
    task_version: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    result: Mapped[str] = mapped_column(String(32), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    __table_args__ = (
        CheckConstraint("result IN ('accepted', 'ignored_stale')", name="ck_reminder_events_result"),
    )

class ReminderStates(Base):
    __tablename__ = 'reminder_states'
    task_id: Mapped[str] = mapped_column(String(128), nullable=False, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    latest_version: Mapped[int] = mapped_column(Integer, nullable=False)
    latest_action: Mapped[str] = mapped_column(String(32), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    __table_args__ = (
        CheckConstraint("latest_action IN ('upsert', 'cancel')", name="ck_reminder_states_latest_action"),
    )

class ReminderJobs(Base):
    __tablename__ = 'reminder_jobs'
    id: Mapped[str] = mapped_column(String(128), nullable=False, primary_key=True, default=new_id)
    task_id: Mapped[str] = mapped_column(String(128), nullable=False)
    task_version: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timezone: Mapped[str] = mapped_column(String(255), nullable=False)
    reminder_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    __table_args__ = (
        CheckConstraint("status IN ('waiting_link', 'pending', 'sending', 'sent', 'cancelled', 'skipped', 'failed')", name="ck_reminder_jobs_status"),
        UniqueConstraint('task_id', 'task_version', name='uq_jobs_task_version'),
        Index('ix_jobs_status_next', 'status', 'next_attempt_at'),
        Index('ix_jobs_user_status', 'user_id', 'status'),
        CheckConstraint('reminder_minutes IN (5, 10, 15, 30)', name='ck_jobs_reminder'),
    )
