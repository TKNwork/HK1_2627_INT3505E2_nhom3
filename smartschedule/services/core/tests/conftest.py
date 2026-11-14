import os
import sys
import pytest
import asyncio
from pathlib import Path
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
)
from services.core.database import get_async_db
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Đảm bảo đường dẫn gốc của smartschedule có trong sys.path để import scripts.*
ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.core.config import Settings
from services.core.database import Base, get_db
from services.core.main import create_app


@pytest.fixture
def settings(tmp_path):
    return Settings(
        _env_file=None,
        jwt_secret='test-jwt-secret-32-characters-minimum',
        internal_api_key='test-internal-key-32-characters-minimum',
        database_url=f"sqlite:///{(tmp_path / 'core.db').as_posix()}",
    )

@pytest.fixture
def async_db_engine(settings):
    url = make_url(settings.database_url).set(
        drivername="sqlite+aiosqlite"
    )

    engine = create_async_engine(url)

    yield engine

    asyncio.run(engine.dispose())

@pytest.fixture
def db_engine(settings):
    engine = create_engine(
        settings.database_url,
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
        echo=False,
    )

    @event.listens_for(engine, 'connect')
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()

    from services.core import models  # noqa: F401 – register models

    # Tạo tất cả các bảng (trước đây chỉ tạo users & refresh_tokens).
    Base.metadata.create_all(engine)

    # User khớp với token trong test_routes.headers(), cần cho khóa ngoại tasks.user_id.
    with engine.begin() as conn:
        conn.execute(models.Users.__table__.insert().values(
            id='test-user',
            email='test-user@example.com',
            password_hash='not-a-real-hash',
        ))

    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    SessionLocal = sessionmaker(bind=db_engine, expire_on_commit=False)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def app(settings, db_engine, async_db_engine):
    application = create_app(
        settings,
        init_database_on_startup=False,
    )

    TestSession = sessionmaker(
        bind=db_engine,
        expire_on_commit=False,
    )

    TestAsyncSession = async_sessionmaker(
        bind=async_db_engine,
        expire_on_commit=False,
    )

    def override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    async def override_get_async_db():
        async with TestAsyncSession() as session:
            yield session

    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_async_db] = override_get_async_db

    return application


@pytest.fixture
def client(app):
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
