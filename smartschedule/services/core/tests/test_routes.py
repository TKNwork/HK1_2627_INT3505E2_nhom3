from datetime import datetime, timedelta, timezone
import jwt
import pytest
from services.core.utils.auth import create_access_token, hash_password, verify_password

TASK = {'title': 'SOA', 'durationMinutes': 90, 'timezone': 'Asia/Ho_Chi_Minh'}
ROUTES = [
    ('post', '/api/v1/auth/register', {'email': 'an@example.com', 'password': 'DemoPass123'}, 201),
    ('post', '/api/v1/auth/login', {'email': 'an@example.com', 'password': 'DemoPass123'}, 200),
    ('post', '/api/v1/tasks', TASK, 201),
    ('get', '/api/v1/tasks?status=pending&scheduled=true&limit=20', None, 200),
    ('get', '/api/v1/tasks/task-stub', None, 200),
    ('patch', '/api/v1/tasks/task-stub', {'expectedVersion': 1, 'title': 'Updated'}, 200),
    ('delete', '/api/v1/tasks/task-stub?expectedVersion=1', None, 204),
    ('post', '/api/v1/tasks/task-stub/complete', {'expectedVersion': 1}, 200),
    ('post', '/api/v1/schedule-drafts', {'sourceText': 'Làm bài SOA', 'timezone': 'Asia/Ho_Chi_Minh'}, 201),
    ('get', '/api/v1/schedule-drafts/draft-stub', None, 200),
    ('patch', '/api/v1/schedule-drafts/draft-stub', {'expectedVersion': 1, 'fields': {'durationMinutes': 60}}, 200),
    ('post', '/api/v1/schedule-drafts/draft-stub/suggestions', {'expectedVersion': 1}, 200),
    ('post', '/api/v1/schedule-drafts/draft-stub/confirm', {'expectedVersion': 1}, 201),
    ('get', '/api/v1/calendar?date=2030-11-02&timezone=Asia/Ho_Chi_Minh', None, 200),
    ('post', '/api/v1/telegram/link-codes', None, 201),
    ('get', '/api/v1/telegram/link', None, 200),
]


def headers(settings):
    token, _ = create_access_token('test-user', settings)
    return {'Authorization': f'Bearer {token}', 'X-Request-Id': 'core-route-test',
            'Idempotency-Key': 'confirm-test-1'}


@pytest.mark.parametrize('method,path,body,status', ROUTES)
def test_all_public_stubs(client, settings, method, path, body, status):
    response = client.request(method, path, json=body, headers=headers(settings))
    assert response.status_code == status, response.text
    assert response.headers['X-Request-Id'] == 'core-route-test'
    if status == 204:
        assert response.content == b''
    else:
        assert set(response.json()) == {'requestId', 'data'}
        assert response.json()['requestId'] == 'core-route-test'


@pytest.mark.parametrize('method,path,body,status', ROUTES[2:])
def test_all_protected_routes_require_jwt(client, method, path, body, status):
    response = client.request(method, path, json=body)
    assert response.status_code == 401, response.text
    assert response.json()['error']['code'] == 'UNAUTHORIZED'


@pytest.mark.parametrize('key', [None, '', '   '])
def test_confirm_requires_idempotency_key(client, settings, key):
    auth = headers(settings)
    auth.pop('Idempotency-Key')
    if key is not None:
        auth['Idempotency-Key'] = key
    response = client.post('/api/v1/schedule-drafts/draft-stub/confirm',
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
def test_validation_envelope(client, settings, method, path, body):
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
                            'exp': datetime.now(timezone.utc)-timedelta(hours=1)},
                           settings.jwt_secret, algorithm='HS256')
    response = client.get('/api/v1/tasks', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 401
    assert response.json()['error']['code'] == 'UNAUTHORIZED'


def test_login_token_works(client):
    response = client.post('/api/v1/auth/login', json={'email': 'an@example.com', 'password': 'DemoPass123'})
    body = response.json()['data']
    assert set(body) == {'user', 'accessToken', 'expiresAt'}
    assert client.get('/api/v1/tasks', headers={'Authorization': 'Bearer '+body['accessToken']}).status_code == 200


def test_password_utilities():
    hashed = hash_password('DemoPass123')
    assert hashed != 'DemoPass123'
    assert verify_password('DemoPass123', hashed)
    assert not verify_password('Wrong', hashed)


def test_all_22_contract_paths_match():
    from scripts.check_contract import main
    main()
