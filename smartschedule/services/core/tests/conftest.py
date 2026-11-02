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
    # Explicitly skip DB initialization; routers do not access DB or other services.
    return create_app(settings, init_database_on_startup=False)


@pytest.fixture
def client(app):
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
