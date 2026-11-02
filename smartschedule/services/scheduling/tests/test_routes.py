import pytest

CASES = [('post', '/internal/v1/conflicts', {'candidate': {'startAt': '2030-11-02T10:00:00+07:00', 'endAt': '2030-11-02T11:00:00+07:00'}, 'busy': []}, 200), ('post', '/internal/v1/suggestions', {'durationMinutes': 90, 'searchFrom': '2030-11-02T08:00:00+07:00', 'searchTo': '2030-11-02T18:00:00+07:00', 'busy': [], 'maxResults': 3}, 200)]


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
