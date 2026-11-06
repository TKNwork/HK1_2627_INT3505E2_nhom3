import pytest
from fastapi.testclient import TestClient
from services.core.config import Settings
from services.core.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None, jwt_secret='test-jwt-secret-32-characters-minimum',
                    internal_api_key='test-internal-key-32-characters-minimum')


@pytest.fixture
def app(settings):
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
    app.state.draft_repository = MemoryDrafts()
    app.dependency_overrides[get_draft_repository] = lambda: app.state.draft_repository
    app.dependency_overrides[get_ai_client] = LocalAI
    return app


@pytest.fixture
def client(app):
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
