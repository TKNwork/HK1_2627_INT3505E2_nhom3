import pytest

CASES = [('post', '/internal/v1/telegram/link-codes', {'userId': 'user-stub'}, 201), ('get', '/internal/v1/telegram/links/user-stub', None, 200), ('post', '/internal/v1/reminder-events', {'eventId': 'evt-stub', 'eventType': 'reminder_changed', 'taskId': 'task-stub', 'taskVersion': 1, 'userId': 'user-stub', 'action': 'upsert', 'reminder': {'title': 'SOA', 'startAt': '2030-11-02T10:00:00+07:00', 'timezone': 'Asia/Ho_Chi_Minh', 'reminderMinutes': 15}}, 200)]


def headers(settings):
    return {'X-Internal-Api-Key': settings.internal_api_key, 'X-Request-Id': 'internal-test'}


@pytest.mark.parametrize('method,path,body,status', CASES)
def test_internal_stubs(client, settings, method, path, body, status):
    response = client.request(method, path, json=body, headers=headers(settings))
    assert response.status_code == status, response.text
    assert set(response.json()) == {'requestId', 'data'}
    assert response.json()['requestId'] == response.headers['X-Request-Id'] == 'internal-test'


@pytest.mark.parametrize('method,path,body,status', CASES)
@pytest.mark.parametrize('key', [None, 'wrong-key'])
def test_internal_auth(client, method, path, body, status, key):
    auth = {} if key is None else {'X-Internal-Api-Key': key}
    response = client.request(method, path, json=body, headers=auth)
    assert response.status_code == 401
    assert response.json()['error']['code'] == 'UNAUTHORIZED'


def test_validation(client, settings):
    method, path, _, _ = next(c for c in CASES if c[0] == 'post')
    response = client.request(method, path, json={}, headers=headers(settings))
    assert response.status_code == 400
    assert response.json()['error']['code'] == 'VALIDATION_ERROR'
    details = response.json()['error']['details']
    assert details and set(details[0]) == {'field', 'reason'}


def test_upsert_requires_reminder(client, settings):
    body = dict(CASES[-1][2])
    body.pop('reminder')
    response = client.post('/internal/v1/reminder-events', json=body, headers=headers(settings))
    assert response.status_code == 400
    assert response.json()['error']['code'] == 'VALIDATION_ERROR'


def test_cancel_without_reminder(client, settings):
    body = dict(CASES[-1][2])
    body.pop('reminder')
    body['action'] = 'cancel'
    response = client.post('/internal/v1/reminder-events', json=body, headers=headers(settings))
    assert response.status_code == 200
    assert response.json()['data'] == {'result': 'accepted'}
