from fastapi import Request
from services.core.utils.errors import AppError, ErrorCode


def test_health(client):
    response = client.get('/health', headers={'X-Request-Id': 'health-test'})
    assert response.status_code == 200
    assert response.json() == {'requestId': 'health-test', 'data': {'service': 'core', 'status': 'ok', 'mode': 'stub'}}
    assert response.headers['X-Request-Id'] == 'health-test'


def test_generated_request_id(client):
    response = client.get('/health')
    assert response.json()['requestId']
    assert response.json()['requestId'] == response.headers['X-Request-Id']


def test_app_error_handler(app, client):
    @app.get('/test-app-error', include_in_schema=False)
    def problem():
        raise AppError(ErrorCode.VALIDATION_ERROR, 400, 'Fixture error',
                       [{'field': 'title', 'reason': 'Required'}])
    response = client.get('/test-app-error', headers={'X-Request-Id': 'error-test'})
    assert response.status_code == 400
    assert response.json() == {'requestId': 'error-test', 'error': {'code': 'VALIDATION_ERROR',
               'message': 'Fixture error', 'details': [{'field': 'title', 'reason': 'Required'}]}}


def test_unexpected_exception_has_envelope(app, client):
    @app.get('/test-unexpected-error', include_in_schema=False)
    def problem():
        raise RuntimeError('private-secret-not-for-response')
    response = client.get('/test-unexpected-error', headers={'X-Request-Id': 'unexpected-test'})
    assert response.status_code == 500
    assert response.json()['error']['code'] == 'INTERNAL_ERROR'
    assert response.headers['X-Request-Id'] == response.json()['requestId'] == 'unexpected-test'
    assert response.json()['error']['details'] == []
    assert 'private-secret' not in response.text


def test_swagger_and_openapi(client):
    assert client.get('/docs').status_code == 200
    assert client.get('/openapi.json').status_code == 200


def test_openapi_validation_error_schema(client):
    schema = client.get('/openapi.json').json()
    assert 'ErrorEnvelope' in schema['components']['schemas']
    for methods in schema['paths'].values():
        for operation in methods.values():
            if operation.get('operationId', '').startswith(('API-', 'INT-')):
                assert '400' in operation['responses']
                assert 'HTTPValidationError' not in str(operation['responses'].get('422', {}))
