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
            with TestSession() as session:
                return session.get(Users, user_id) is not None

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
    from services.core.models import Users
    TestSession = sessionmaker(bind=db_engine, expire_on_commit=False)
    with TestSession() as session:
        session.add_all([Users(id='test-user', email='test@example.com', password_hash='test'),
                         Users(id='other-user', email='other@example.com', password_hash='test')])
        session.commit()

    def override_get_db():
        with TestSession() as session:
            yield session

    app.state.test_session = TestSession
    app.dependency_overrides[get_db] = override_get_db
    app.state.draft_repository = MemoryDrafts()
    app.dependency_overrides[get_draft_repository] = lambda: app.state.draft_repository
    app.dependency_overrides[get_ai_client] = LocalAI
    return app

@pytest.fixture
def client(app):
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
