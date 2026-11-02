import asyncio
import httpx
import pytest
from services.core.clients.ai_client import AIClient
from services.core.clients.scheduling_client import SchedulingClient
from services.core.clients.notification_client import NotificationClient
from services.core.utils.errors import AppError


def test_client_propagates_headers(settings):
    def handler(request):
        assert request.headers['X-Request-Id'] == 'trace-client'
        assert request.headers['X-Internal-Api-Key'] == settings.internal_api_key
        assert request.url.path == '/internal/v1/extractions'
        return httpx.Response(200, json={'requestId': 'trace-client', 'data': {'fields': {}}})
    client = AIClient(settings, transport=httpx.MockTransport(handler))
    assert asyncio.run(client.extract({'sourceText': 'SOA'}, 'trace-client')) == {'fields': {}}
    assert settings.ai_timeout_seconds > settings.scheduling_timeout_seconds


@pytest.mark.parametrize('failure,status,code', [
    ('timeout', 504, 'AI_TIMEOUT'),
    ('unavailable', 503, 'AI_UNAVAILABLE'),
    ('json', 502, 'AI_INVALID_RESPONSE'),
])
def test_client_errors_are_app_errors(settings, failure, status, code):
    def handler(request):
        if failure == 'timeout':
            raise httpx.ReadTimeout('test', request=request)
        if failure == 'unavailable':
            return httpx.Response(503)
        return httpx.Response(200, text='not-json')
    client = AIClient(settings, transport=httpx.MockTransport(handler))
    with pytest.raises(AppError) as error:
        asyncio.run(client.extract({}, 'trace-client'))
    assert error.value.code == code
    assert error.value.http_status == status


def test_other_client_paths_and_methods(settings):
    paths = []
    def handler(request):
        paths.append((request.method, request.url.path))
        return httpx.Response(200, json={'requestId': 'trace', 'data': {}})
    transport = httpx.MockTransport(handler)
    async def call():
        scheduling = SchedulingClient(settings, transport=transport)
        await scheduling.conflicts({}, 'trace')
        await scheduling.suggestions({}, 'trace')
        notification = NotificationClient(settings, transport=transport)
        await notification.link_code({}, 'trace')
        await notification.reminder_event({}, 'trace')
        await notification.link_status('user-stub', 'trace')
    asyncio.run(call())
    assert paths == [('POST', '/internal/v1/conflicts'), ('POST', '/internal/v1/suggestions'),
                     ('POST', '/internal/v1/telegram/link-codes'), ('POST', '/internal/v1/reminder-events'),
                     ('GET', '/internal/v1/telegram/links/user-stub')]
