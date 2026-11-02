from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from .config import Settings


class Base(DeclarativeBase):
    pass


@lru_cache(maxsize=4)
def get_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)


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
