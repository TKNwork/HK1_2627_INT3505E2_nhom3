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
def app(settings):
    """Dùng DB và AI giả để kiểm thử Core mà không gọi dịch vụ ngoài."""
    from datetime import datetime, timedelta, timezone
    from services.core.models import ScheduleDrafts
    from services.core.services.drafts import get_ai_client, get_draft_repository
    from services.core.services.fixtures import stub_draft
    from services.ai.schemas.extractions import ExtractionRequest
    from services.ai.services.extraction import extract_rules

    class MemoryDrafts:
        def __init__(self):
            draft = stub_draft().model_dump()
            self.rows = {'draft-stub': ScheduleDrafts(**draft, user_id='test-user')}
            self.rows['draft-stub'].expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

        def user_exists(self, user_id):
            return user_id in ('test-user', 'other-user')

        def add(self, row):
            self.rows[row.id] = row
            return row

        def find_owned(self, draft_id, user_id):
            row = self.rows.get(draft_id)
            return row if row is not None and row.user_id == user_id else None

    class LocalAI:
        async def extract(self, payload, request_id):
            return extract_rules(ExtractionRequest.model_validate(payload)).model_dump(mode='json', by_alias=True)

    app = create_app(settings, init_database_on_startup=False)
    from unittest.mock import MagicMock
    from services.core.database import get_db
    from services.core.models import Users
    app.state.users = {'test-user', 'other-user', 'user-stub'}
    app.state.auth_session = MagicMock()
    app.state.auth_session.get.side_effect = lambda model, user_id: (
        Users(id=user_id) if user_id in app.state.users else None)
    app.dependency_overrides[get_db] = lambda: app.state.auth_session
    app.state.draft_repository = MemoryDrafts()
    app.dependency_overrides[get_draft_repository] = lambda: app.state.draft_repository
    app.dependency_overrides[get_ai_client] = LocalAI
    return app
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
