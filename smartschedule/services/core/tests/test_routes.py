from datetime import datetime, timedelta, timezone
import jwt
import pytest
from services.core.utils.auth import create_access_token, hash_password, verify_password

TASK = {'title': 'SOA', 'durationMinutes': 90, 'timezone': 'Asia/Ho_Chi_Minh'}

# Shared routes that use the standard app fixture.
STUB_ROUTES = [
    ('post', '/api/v1/tasks', TASK, 201),
    ('get', '/api/v1/tasks?status=pending&scheduled=true&limit=20', None, 200),
    ('get', '/api/v1/tasks/task-stub', None, 200),
    ('patch', '/api/v1/tasks/task-stub', {'expectedVersion': 1, 'title': 'Updated'}, 200),
    ('delete', '/api/v1/tasks/task-stub?expectedVersion=1', None, 204),
    ('post', '/api/v1/tasks/task-stub/complete', {'expectedVersion': 1}, 200),
    ('get', '/api/v1/calendar?date=2030-11-02&timezone=Asia/Ho_Chi_Minh', None, 200),
    ('post', '/api/v1/telegram/link-codes', None, 201),
    ('get', '/api/v1/telegram/link', None, 200),
]

DRAFT_ROUTES = [
    ('post', '/api/v1/schedule-drafts', {'sourceText': 'Làm bài SOA', 'timezone': 'Asia/Ho_Chi_Minh'}, 201),
    ('get', '/api/v1/schedule-drafts/draft-stub', None, 200),
    ('patch', '/api/v1/schedule-drafts/draft-stub', {'expectedVersion': 1, 'fields': {'durationMinutes': 60}}, 501),
    ('post', '/api/v1/schedule-drafts/draft-stub/suggestions', {'expectedVersion': 1}, 501),
    ('post', '/api/v1/schedule-drafts/draft-stub/confirm', {'expectedVersion': 1}, 422),
]


def headers(settings):
    token, _ = create_access_token('test-user', settings)
    return {'Authorization': f'Bearer {token}', 'X-Request-Id': 'core-route-test',
            'Idempotency-Key': 'confirm-test-1'}


# ── UC-01: Register ──────────────────────────────────────────────────────

def test_register_success(auth_client):
    response = auth_client.post('/api/v1/auth/register',
                           json={'email': 'new@example.com', 'password': 'DemoPass123'},
                           headers={'X-Request-Id': 'reg-test'})
    assert response.status_code == 201, response.text
    data = response.json()['data']
    assert data['user']['email'] == 'new@example.com'
    assert data['user']['id']


def test_register_duplicate_email(auth_client):
    auth_client.post('/api/v1/auth/register',
                json={'email': 'dup@example.com', 'password': 'DemoPass123'})
    response = auth_client.post('/api/v1/auth/register',
                           json={'email': 'dup@example.com', 'password': 'OtherPass123'})
    assert response.status_code == 409
    assert response.json()['error']['code'] == 'EMAIL_ALREADY_EXISTS'


def test_register_normalizes_email(auth_client):
    response = auth_client.post('/api/v1/auth/register',
                           json={'email': '  Upper@Example.COM  ', 'password': 'DemoPass123'})
    assert response.status_code == 201
    assert response.json()['data']['user']['email'] == 'upper@example.com'


# ── UC-02: Login ──────────────────────────────────────────────────────────

def test_login_success(auth_client):
    auth_client.post('/api/v1/auth/register',
                json={'email': 'login@example.com', 'password': 'DemoPass123'})
    response = auth_client.post('/api/v1/auth/login',
                           json={'email': 'login@example.com', 'password': 'DemoPass123'})
    assert response.status_code == 200, response.text
    data = response.json()['data']
    assert set(data) == {'user', 'accessToken', 'refreshToken', 'expiresIn', 'expiresAt'}
    assert data['user']['email'] == 'login@example.com'
    assert data['expiresIn'] == 600  # 10 minutes = 600 seconds


def test_login_wrong_password(auth_client):
    auth_client.post('/api/v1/auth/register',
                json={'email': 'wrong@example.com', 'password': 'DemoPass123'})
    response = auth_client.post('/api/v1/auth/login',
                           json={'email': 'wrong@example.com', 'password': 'WrongPassword1'})
    assert response.status_code == 401
    assert response.json()['error']['code'] == 'INVALID_CREDENTIALS'


def test_login_nonexistent_user(auth_client):
    response = auth_client.post('/api/v1/auth/login',
                           json={'email': 'ghost@example.com', 'password': 'DemoPass123'})
    assert response.status_code == 401
    assert response.json()['error']['code'] == 'INVALID_CREDENTIALS'


def test_login_token_works_for_protected_routes(auth_client, settings):
    auth_client.post('/api/v1/auth/register',
                json={'email': 'token@example.com', 'password': 'DemoPass123'})
    login_resp = auth_client.post('/api/v1/auth/login',
                             json={'email': 'token@example.com', 'password': 'DemoPass123'})
    access_token = login_resp.json()['data']['accessToken']
    tasks_resp = auth_client.get('/api/v1/tasks',
                            headers={'Authorization': f'Bearer {access_token}'})
    assert tasks_resp.status_code == 200


# ── Refresh token ─────────────────────────────────────────────────────────

def test_refresh_token_rotation(auth_client):
    auth_client.post('/api/v1/auth/register',
                json={'email': 'refresh@example.com', 'password': 'DemoPass123'})
    login_resp = auth_client.post('/api/v1/auth/login',
                             json={'email': 'refresh@example.com', 'password': 'DemoPass123'})
    refresh_token = login_resp.json()['data']['refreshToken']

    refresh_resp = auth_client.post('/api/v1/auth/refresh',
                               json={'refreshToken': refresh_token})
    assert refresh_resp.status_code == 200
    data = refresh_resp.json()['data']
    assert set(data) == {'accessToken', 'refreshToken', 'expiresIn', 'expiresAt'}
    assert data['refreshToken'] != refresh_token

    reuse_resp = auth_client.post('/api/v1/auth/refresh',
                             json={'refreshToken': refresh_token})
    assert reuse_resp.status_code == 401


def test_logout_revokes_refresh_token(auth_client):
    auth_client.post('/api/v1/auth/register',
                json={'email': 'logout@example.com', 'password': 'DemoPass123'})
    login_resp = auth_client.post('/api/v1/auth/login',
                             json={'email': 'logout@example.com', 'password': 'DemoPass123'})
    refresh_token = login_resp.json()['data']['refreshToken']

    logout_resp = auth_client.post('/api/v1/auth/logout',
                              json={'refreshToken': refresh_token})
    assert logout_resp.status_code == 204

    refresh_resp = auth_client.post('/api/v1/auth/refresh',
                               json={'refreshToken': refresh_token})
    assert refresh_resp.status_code == 401


# ── Stub routes ──────────────────────────────────────────────────────────

@pytest.mark.parametrize('method,path,body,status', STUB_ROUTES)
def test_stub_routes(client, settings, method, path, body, status):
    response = client.request(method, path, json=body, headers=headers(settings))
    assert response.status_code == status, response.text
    assert response.headers['X-Request-Id'] == 'core-route-test'
    if status == 204:
        assert response.content == b''
    else:
        assert set(response.json()) == {'requestId', 'data'}
        assert response.json()['requestId'] == 'core-route-test'


@pytest.mark.parametrize('method,path,body,status', DRAFT_ROUTES)
def test_draft_routes(draft_client, settings, method, path, body, status):
    response = draft_client.request(method, path, json=body, headers=headers(settings))
    assert response.status_code == status, response.text
    if status == 501:
        assert response.json()['error']['code'] == 'NOT_IMPLEMENTED'


@pytest.mark.parametrize('method,path,body,status', STUB_ROUTES + DRAFT_ROUTES)
def test_all_protected_routes_require_jwt(client, method, path, body, status):
    response = client.request(method, path, json=body)
    assert response.status_code == 401, response.text
    assert response.json()['error']['code'] == 'UNAUTHORIZED'


@pytest.mark.parametrize('key', [None, '', '   '])
def test_confirm_requires_idempotency_key(draft_client, settings, key):
    auth = headers(settings)
    auth.pop('Idempotency-Key')
    if key is not None:
        auth['Idempotency-Key'] = key
    response = draft_client.post('/api/v1/schedule-drafts/draft-stub/confirm',
                           json={'expectedVersion': 1}, headers=auth)
    assert response.status_code == 400
    assert response.json()['error']['code'] == 'IDEMPOTENCY_KEY_REQUIRED'


@pytest.mark.parametrize('method,path,body', [
    ('post', '/api/v1/auth/register', {'email': 'bad', 'password': 'short'}),
    ('post', '/api/v1/tasks', {'title': 'SOA', 'durationMinutes': 0, 'timezone': 'Asia/Ho_Chi_Minh'}),
    ('post', '/api/v1/tasks', {**TASK, 'startAt': '2030-11-02T10:00:00'}),
    ('post', '/api/v1/tasks', {**TASK, 'timezone': 'Not/AZone'}),
    ('patch', '/api/v1/tasks/task-stub', {'title': 'Missing version'}),
    ('delete', '/api/v1/tasks/task-stub', None),
    ('post', '/api/v1/tasks/task-stub/complete', {}),
    ('patch', '/api/v1/schedule-drafts/draft-stub', {'expectedVersion': 1, 'durationMinutes': 60}),
    ('get', '/api/v1/tasks?limit=101', None),
    ('get', '/api/v1/calendar?date=bad&timezone=Asia/Ho_Chi_Minh', None),
])
def test_validation_envelope(request, settings, method, path, body):
    if '/schedule-drafts' in path:
        client = request.getfixturevalue('draft_client')
    elif '/auth/' in path:
        client = request.getfixturevalue('auth_client')
    else:
        client = request.getfixturevalue('client')
    response = client.request(method, path, json=body, headers=headers(settings))
    assert response.status_code == 400
    data = response.json()
    assert set(data) == {'requestId', 'error'}
    assert data['error']['code'] == 'VALIDATION_ERROR'
    assert data['error']['details']
    assert set(data['error']['details'][0]) == {'field', 'reason'}


def test_invalid_json_is_normalized(client, settings):
    response = client.post('/api/v1/tasks', content='{bad', headers=headers(settings))
    assert response.status_code == 400
    assert response.json()['error']['code'] == 'VALIDATION_ERROR'


@pytest.mark.parametrize('kind', ['invalid', 'expired'])
def test_invalid_jwt(client, settings, kind):
    token = 'not-a-token'
    if kind == 'expired':
        token = jwt.encode({'sub': 'x', 'iat': datetime.now(timezone.utc)-timedelta(hours=2),
                            'exp': datetime.now(timezone.utc)-timedelta(hours=1),
                            'type': 'access'},
                           settings.jwt_secret, algorithm='HS256')
    response = client.get('/api/v1/tasks', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 401
    assert response.json()['error']['code'] == 'UNAUTHORIZED'


def test_password_utilities():
    hashed = hash_password('DemoPass123')
    assert hashed != 'DemoPass123'
    assert verify_password('DemoPass123', hashed)
    assert not verify_password('Wrong', hashed)


def test_all_22_contract_paths_match():
    from scripts.check_contract import main
    main()


@pytest.mark.parametrize('path', [
    '/api/v1/tasks',
    '/api/v1/calendar?date=2030-11-02&timezone=Asia/Ho_Chi_Minh',
    '/api/v1/telegram/link',
])
def test_shared_routes_accept_legacy_jwt_without_database(client, settings, path):
    now = datetime.now(timezone.utc)
    token = jwt.encode({'sub': 'team-test-user', 'iat': now, 'exp': now + timedelta(minutes=5)},
                       settings.jwt_secret, algorithm='HS256')
    assert client.get(path, headers={'Authorization': f'Bearer {token}'}).status_code == 200


def test_expired_rotated_token_preserves_current_session(auth_client, auth_app):
    from sqlalchemy import update
    from services.core.models import RefreshTokens
    from services.core.utils.auth import hash_refresh_token

    credentials = {'email': 'expired@example.com', 'password': 'DemoPass123'}
    assert auth_client.post('/api/v1/auth/register', json=credentials).status_code == 201
    logged_in = auth_client.post('/api/v1/auth/login', json=credentials).json()['data']
    path = '/api/v1/auth/refresh'
    first = {'refreshToken': logged_in['refreshToken']}
    second = {'refreshToken': auth_client.post(path, json=first).json()['data']['refreshToken']}
    with auth_app.state.test_session.begin() as session:
        session.execute(update(RefreshTokens).where(
            RefreshTokens.token_hash == hash_refresh_token(first['refreshToken']),
        ).values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
    assert auth_client.post(path, json=first).status_code == 401
    assert auth_client.post(path, json=second).status_code == 200
