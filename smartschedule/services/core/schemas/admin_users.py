from datetime import datetime, timezone
from pydantic import Field, field_validator
from .base import ApiModel


class AdminCreateUserRequest(ApiModel):
    email: str = Field(min_length=3, max_length=254, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default='user', pattern=r'^(user|admin)$')

    @field_validator('email', mode='before')
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower() if isinstance(v, str) else v


class AdminUpdateUserRequest(ApiModel):
    email: str | None = Field(default=None, min_length=3, max_length=254, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: str | None = Field(default=None, pattern=r'^(user|admin)$')

    @field_validator('email', mode='before')
    @classmethod
    def normalize_email(cls, v: str | None) -> str | None:
        return v.strip().lower() if isinstance(v, str) else v


class UserDetail(ApiModel):
    id: str
    email: str
    role: str
    created_at: datetime
    updated_at: datetime

    @field_validator('created_at', 'updated_at', mode='before')
    @classmethod
    def ensure_timezone(cls, v: datetime | str) -> datetime | str:
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class UserListResponse(ApiModel):
    total: int
    items: list[UserDetail]
