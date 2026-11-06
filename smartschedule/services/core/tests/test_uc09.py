from datetime import datetime, timedelta, timezone
import httpx
import pytest
from services.core.clients.ai_client import AIClient
from services.core.services.drafts import get_ai_client
from services.core.utils.auth import create_access_token
from services.ai.config import Settings as AISettings
from services.ai.main import create_app as create_ai_app
from .test_routes import headers

TEXT = 'Ngày mai làm bài SOA trong 90 phút, xong trước 17 giờ'
PAYLOAD = {'sourceText': TEXT, 'timezone': 'Asia/Ho_Chi_Minh', 'referenceTime': '2026-11-06T10:00:00+07:00'}


def test_create_then_read_draft(client, app, settings):
    before = datetime.now(timezone.utc)
    response = client.post('/api/v1/schedule-drafts', json=PAYLOAD, headers=headers(settings))
    assert response.status_code == 201, response.text
    draft = response.json()['data']['draft']
    assert draft['fields']['title'] == 'làm bài SOA'
    assert draft['fields']['date'] == '2026-11-07'
    assert draft['fields']['durationMinutes'] == 90
    assert draft['fields']['deadlineAt'] == '2026-11-07T10:00:00Z'
    assert draft['state'] == 'ready_to_schedule'
    assert draft['missingFields'] == ['startAt']
    assert draft['requiredInputFields'] == []
    assert draft['suggestions'] == [] and draft['confirmedTaskId'] is None
    assert draft['version'] == 1
    expires = datetime.fromisoformat(draft['expiresAt'].replace('Z', '+00:00'))
    assert before + timedelta(minutes=30) <= expires <= datetime.now(timezone.utc) + timedelta(minutes=30)
    read = client.get('/api/v1/schedule-drafts/' + draft['id'], headers=headers(settings))
    assert read.json()['data']['draft'] == draft
    assert app.state.draft_repository.rows[draft['id']].user_id == 'test-user'


@pytest.mark.parametrize('method,suffix,body', [('get', '', None),
    ('patch', '', {'expectedVersion': 1, 'fields': {'title': 'Hacked'}}),
    ('post', '/suggestions', {'expectedVersion': 1}), ('post', '/confirm', {'expectedVersion': 1})])
def test_bola(client, settings, method, suffix, body):
    auth = headers(settings)
    auth['Authorization'] = 'Bearer ' + create_access_token('other-user', settings)[0]
    response = client.request(method, '/api/v1/schedule-drafts/draft-stub' + suffix, json=body, headers=auth)
    assert response.status_code == 404
    assert response.json()['error']['code'] == 'DRAFT_NOT_FOUND'


def test_expired_and_missing(client, app, settings):
    app.state.draft_repository.rows['draft-stub'].expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert client.get('/api/v1/schedule-drafts/draft-stub', headers=headers(settings)).status_code == 410
    assert client.get('/api/v1/schedule-drafts/missing', headers=headers(settings)).status_code == 404


@pytest.mark.parametrize('payload', [{'text': '  '}, {'text': 'SOA', 'timezone': 'Invalid/Zone'},
    {'text': 'SOA', 'reference_time': '2026-11-06T10:00:00'}])
def test_invalid_input(client, settings, payload):
    assert client.post('/api/v1/schedule-drafts', json=payload, headers=headers(settings)).status_code == 400


@pytest.mark.parametrize('result', [{'fields': {'durationMinutes': 0}, 'warnings': []},
    {'fields': {'startAt': '2026-11-07T09:00:00'}, 'warnings': []},
    {'fields': {}, 'warnings': 'invalid'}, {}, {'fields': {'title': '  '}, 'warnings': []},
    {'fields': {'date': '2026-11-08', 'startAt': '2026-11-07T09:00:00+07:00'}, 'warnings': []}])
def test_invalid_ai_does_not_save(client, app, settings, result):
    class BadAI:
        async def extract(self, payload, request_id):
            return result
    app.dependency_overrides[get_ai_client] = BadAI
    response = client.post('/api/v1/schedule-drafts', json=PAYLOAD, headers=headers(settings))
    assert response.status_code == 502, response.text
    assert list(app.state.draft_repository.rows) == ['draft-stub']


@pytest.mark.parametrize('text,state,required', [('Làm bài SOA', 'needs_input', ['durationMinutes', 'date']),
    ('Ngày mai họp lúc 9h trong 60 phút', 'ready_to_confirm', []),
    ('Ngày mai học SOA lúc 16h trong 90 phút, xong trước 17h', 'needs_input', ['deadlineAt'])])
def test_states(client, settings, text, state, required):
    response = client.post('/api/v1/schedule-drafts', json={**PAYLOAD, 'sourceText': text}, headers=headers(settings))
    draft = response.json()['data']['draft']
    assert draft['state'] == state
    assert draft['requiredInputFields'] == required


def test_deleted_user_rejected(client, settings):
    auth = headers(settings)
    auth['Authorization'] = 'Bearer ' + create_access_token('deleted-user', settings)[0]
    assert client.post('/api/v1/schedule-drafts', json=PAYLOAD, headers=auth).status_code == 401


def test_core_to_ai_transport(client, app, settings):
    ai_app = create_ai_app(AISettings(_env_file=None, internal_api_key=settings.internal_api_key))
    app.dependency_overrides[get_ai_client] = lambda: AIClient(settings, transport=httpx.ASGITransport(app=ai_app))
    response = client.post('/api/v1/schedule-drafts', json=PAYLOAD, headers=headers(settings))
    assert response.status_code == 201, response.text
    assert response.json()['requestId'] == 'core-route-test'
    assert response.json()['data']['draft']['fields']['durationMinutes'] == 90


@pytest.mark.parametrize('status,code', [(502, 'AI_INVALID_RESPONSE'), (503, 'AI_UNAVAILABLE'), (504, 'AI_TIMEOUT')])
def test_upstream_error_mapping(client, app, settings, status, code):
    app.dependency_overrides[get_ai_client] = lambda: AIClient(settings,
        transport=httpx.MockTransport(lambda request: httpx.Response(status)))
    response = client.post('/api/v1/schedule-drafts', json=PAYLOAD, headers=headers(settings))
    assert response.status_code == status
    assert response.json()['error']['code'] == code
    assert list(app.state.draft_repository.rows) == ['draft-stub']
