import os
import sys
from pathlib import Path
import pytest
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
def settings() -> Settings:
    return Settings(_env_file=None, jwt_secret='test-jwt-secret-32-characters-minimum',
                    internal_api_key='test-internal-key-32-characters-minimum',
                    database_url='sqlite://')


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

    # Tạo các bảng cần thiết cho auth (users & refresh_tokens)
    auth_tables = [models.Users.__table__, models.RefreshTokens.__table__]
    Base.metadata.create_all(engine, tables=auth_tables)
    yield engine
    Base.metadata.drop_all(engine, tables=auth_tables)
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    SessionLocal = sessionmaker(bind=db_engine, expire_on_commit=False)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def app(settings, db_engine):
    application = create_app(settings, init_database_on_startup=False)

    TestSession = sessionmaker(bind=db_engine, expire_on_commit=False)

    def override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    application.dependency_overrides[get_db] = override_get_db
    return application


@pytest.fixture
def client(app):
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
