from pydantic import AwareDatetime, Field, field_validator
from .base import ApiModel


class Credentials(ApiModel):
    email: str = Field(min_length=3, max_length=254, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    password: str = Field(min_length=8, max_length=128)

    @field_validator('email', mode='before')
    @classmethod
    def strip_email(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


class RefreshRequest(ApiModel):
    refresh_token: str = Field(min_length=1)


class User(ApiModel):
    id: str
    email: str
    role: str = 'user'


class RegisterData(ApiModel):
    user: User


class LoginData(ApiModel):
    user: User
    access_token: str
    refresh_token: str
    expires_in: int  # access token TTL in seconds
    expires_at: AwareDatetime


class RefreshData(ApiModel):
    access_token: str
    refresh_token: str
    expires_in: int
    expires_at: AwareDatetime
