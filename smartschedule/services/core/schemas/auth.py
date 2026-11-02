from pydantic import AwareDatetime, Field
from .base import ApiModel


class Credentials(ApiModel):
    email: str = Field(min_length=3, max_length=254, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    password: str = Field(min_length=8, max_length=128)


class User(ApiModel):
    id: str
    email: str


class RegisterData(ApiModel):
    user: User


class LoginData(ApiModel):
    user: User
    access_token: str
    expires_at: AwareDatetime
