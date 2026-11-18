import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.core.config import Settings
from services.core.database import Base, get_db
from services.core.main import create_app
from services.core.models import RefreshTokens, Users
from services.core.utils.auth import create_access_token, hash_password


@pytest.fixture
def core_settings() -> Settings:
    return Settings(
        _env_file=None,
        jwt_secret='test-jwt-secret-32-characters-minimum',
        internal_api_key='test-internal-key-32-characters-minimum',
        database_url='sqlite://',
    )


@pytest.fixture
def rbac_client(core_settings):
    engine = create_engine(
        core_settings.database_url,
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    auth_tables = [Users.__table__, RefreshTokens.__table__]
    Base.metadata.create_all(engine, tables=auth_tables)
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False)

    with TestingSession() as session:
        session.add_all([
            Users(id='admin-001', email='admin@example.com', password_hash=hash_password('AdminPass123'), role='admin'),
            Users(id='user-001', email='user@example.com', password_hash=hash_password('UserPass123'), role='user'),
        ])
        session.commit()

    app = create_app(core_settings, init_database_on_startup=False)

    def override_get_db():
        with TestingSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.state.TestingSession = TestingSession

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine, tables=auth_tables)
    engine.dispose()


def auth_header(user_id: str, role: str, settings: Settings) -> dict:
    token, _ = create_access_token(user_id, settings, role=role)
    return {'Authorization': f'Bearer {token}', 'X-Request-Id': 'req-test-rbac'}


# ---------------------------------------------------------------------------
# Tests: Role-Based Access Control (RBAC) Permissions
# ---------------------------------------------------------------------------

def test_unauthenticated_cannot_access_admin_endpoints(rbac_client):
    response = rbac_client.get('/api/v1/admin/users', headers={'X-Request-Id': 'req-01'})
    assert response.status_code == 401
    assert response.json()['error']['code'] == 'UNAUTHORIZED'


def test_regular_user_forbidden_from_admin_endpoints(rbac_client, core_settings):
    headers = auth_header('user-001', 'user', core_settings)
    response = rbac_client.get('/api/v1/admin/users', headers=headers)
    assert response.status_code == 403
    assert response.json()['error']['code'] == 'FORBIDDEN'


# ---------------------------------------------------------------------------
# Tests: Admin User CRUD Operations
# ---------------------------------------------------------------------------

def test_admin_list_users(rbac_client, core_settings):
    headers = auth_header('admin-001', 'admin', core_settings)
    response = rbac_client.get('/api/v1/admin/users', headers=headers)
    assert response.status_code == 200
    data = response.json()['data']
    assert data['total'] >= 2
    emails = [item['email'] for item in data['items']]
    assert 'admin@example.com' in emails
    assert 'user@example.com' in emails


def test_admin_list_users_with_filter(rbac_client, core_settings):
    headers = auth_header('admin-001', 'admin', core_settings)

    # Filter by role
    response = rbac_client.get('/api/v1/admin/users?role=admin', headers=headers)
    assert response.status_code == 200
    items = response.json()['data']['items']
    assert all(item['role'] == 'admin' for item in items)

    # Filter by search
    response = rbac_client.get('/api/v1/admin/users?search=user@', headers=headers)
    assert response.status_code == 200
    items = response.json()['data']['items']
    assert len(items) == 1
    assert items[0]['email'] == 'user@example.com'


def test_admin_get_user_detail(rbac_client, core_settings):
    headers = auth_header('admin-001', 'admin', core_settings)
    response = rbac_client.get('/api/v1/admin/users/user-001', headers=headers)
    assert response.status_code == 200
    user_data = response.json()['data']
    assert user_data['id'] == 'user-001'
    assert user_data['email'] == 'user@example.com'
    assert user_data['role'] == 'user'


def test_admin_get_nonexistent_user(rbac_client, core_settings):
    headers = auth_header('admin-001', 'admin', core_settings)
    response = rbac_client.get('/api/v1/admin/users/non-existent-id', headers=headers)
    assert response.status_code == 404
    assert response.json()['error']['code'] == 'USER_NOT_FOUND'


def test_admin_create_user(rbac_client, core_settings):
    headers = auth_header('admin-001', 'admin', core_settings)
    payload = {
        'email': 'newstudent@example.com',
        'password': 'Password123!',
        'role': 'user',
    }
    response = rbac_client.post('/api/v1/admin/users', json=payload, headers=headers)
    assert response.status_code == 201
    created = response.json()['data']
    assert created['email'] == 'newstudent@example.com'
    assert created['role'] == 'user'
    assert 'id' in created


def test_admin_create_duplicate_email_fails(rbac_client, core_settings):
    headers = auth_header('admin-001', 'admin', core_settings)
    payload = {
        'email': 'user@example.com',
        'password': 'Password123!',
        'role': 'user',
    }
    response = rbac_client.post('/api/v1/admin/users', json=payload, headers=headers)
    assert response.status_code == 409
    assert response.json()['error']['code'] == 'EMAIL_ALREADY_EXISTS'


def test_admin_update_user(rbac_client, core_settings):
    headers = auth_header('admin-001', 'admin', core_settings)
    payload = {
        'email': 'updated_user@example.com',
        'role': 'admin',
    }
    response = rbac_client.patch('/api/v1/admin/users/user-001', json=payload, headers=headers)
    assert response.status_code == 200
    updated = response.json()['data']
    assert updated['email'] == 'updated_user@example.com'
    assert updated['role'] == 'admin'


def test_admin_cannot_demote_themself_if_sole_admin(rbac_client, core_settings):
    headers = auth_header('admin-001', 'admin', core_settings)
    payload = {'role': 'user'}
    response = rbac_client.patch('/api/v1/admin/users/admin-001', json=payload, headers=headers)
    assert response.status_code == 400
    assert response.json()['error']['code'] == 'VALIDATION_ERROR'


def test_admin_cannot_delete_themself(rbac_client, core_settings):
    headers = auth_header('admin-001', 'admin', core_settings)
    response = rbac_client.delete('/api/v1/admin/users/admin-001', headers=headers)
    assert response.status_code == 400
    assert response.json()['error']['code'] == 'VALIDATION_ERROR'


def test_admin_delete_user_success(rbac_client, core_settings):
    headers = auth_header('admin-001', 'admin', core_settings)
    response = rbac_client.delete('/api/v1/admin/users/user-001', headers=headers)
    assert response.status_code == 204

    # Verify deleted
    with rbac_client.app.state.TestingSession() as session:
        user = session.get(Users, 'user-001')
        assert user is None
