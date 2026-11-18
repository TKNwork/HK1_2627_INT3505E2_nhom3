import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from services.core.config import Settings
from services.core.database import Base, get_db
from services.core.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None, jwt_secret='test-jwt-secret-32-characters-minimum',
                    internal_api_key='test-internal-key-32-characters-minimum')


@pytest.fixture
def auth_db_engine():
    engine = create_engine(
        'sqlite://',
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
def app(settings):
    return create_app(settings, init_database_on_startup=False)


@pytest.fixture
def client(app):
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def auth_app(app, auth_db_engine):
    test_session = sessionmaker(bind=auth_db_engine, expire_on_commit=False)

    def override_get_db():
        with test_session() as session:
            yield session

    app.state.test_session = test_session
    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.fixture
def auth_client(auth_app):
    with TestClient(auth_app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def draft_app(auth_app):
    from datetime import datetime, timedelta, timezone
    from services.core.models import ScheduleDrafts, Users
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
            with auth_app.state.test_session() as session:
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

    with auth_app.state.test_session() as session:
        session.add_all([Users(id='test-user', email='test@example.com', password_hash='test'),
                         Users(id='other-user', email='other@example.com', password_hash='test')])
        session.commit()

    auth_app.state.draft_repository = MemoryDrafts()
    auth_app.dependency_overrides[get_draft_repository] = lambda: auth_app.state.draft_repository
    auth_app.dependency_overrides[get_ai_client] = LocalAI
    return auth_app

@pytest.fixture
def draft_client(draft_app):
    with TestClient(draft_app, raise_server_exceptions=False) as test_client:
        yield test_client
