from collections.abc import Iterator, AsyncIterator
from contextlib import contextmanager
from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from .config import Settings
from fastapi import Request
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


class Base(DeclarativeBase):
    pass


@lru_cache(maxsize=4)
def get_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)

@lru_cache(maxsize=4)
def get_async_engine(database_url: str):
    url = make_url(database_url)

    if url.get_backend_name() == "postgresql":
        url = url.set(drivername="postgresql+asyncpg")
    elif url.get_backend_name() == "sqlite":
        url = url.set(drivername="sqlite+aiosqlite")
    else:
        raise ValueError("Database driver chưa hỗ trợ AsyncSession")

    return create_async_engine(
        url,
        pool_pre_ping=True,
    )


@lru_cache(maxsize=4)
def get_async_session_factory(database_url: str):
    return async_sessionmaker(
        bind=get_async_engine(database_url),
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_async_db(
    request: Request,
) -> AsyncIterator[AsyncSession]:

    settings = request.app.state.settings

    factory = get_async_session_factory(
        settings.database_url
    )

    async with factory() as session:
        yield session

def SessionLocal() -> Session:
    settings = Settings()
    return sessionmaker(bind=get_engine(settings.database_url), expire_on_commit=False)()


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


@contextmanager
def transaction(session: Session) -> Iterator[Session]:
    # TODO: chốt ranh giới transaction và khóa chống overlap khi làm nghiệp vụ.
    with session.begin():
        yield session


def init_database(settings: Settings) -> None:
    from . import models  # Register only this service's metadata.
    # TODO: thay create_all bằng Alembic khi bắt đầu quản lý migration.
    Base.metadata.create_all(get_engine(settings.database_url))
