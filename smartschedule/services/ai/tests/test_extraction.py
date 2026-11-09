import asyncio
import json
import httpx
import pytest
from services.ai.schemas.extractions import ExtractionRequest, ExtractionFields
from services.ai.services.extraction import extract_rules
from services.ai.services.provider import extract_request
from services.ai.clients.llm_client import LLMClient

NOW = '2026-11-06T10:00:00+07:00'


def body(text, now=NOW, zone='Asia/Ho_Chi_Minh'):
    return ExtractionRequest(source_text=text, timezone=zone, now=now)


@pytest.mark.parametrize('text,date,start,duration,deadline', [
    ('Ngày mai làm bài SOA trong 90 phút, xong trước 17 giờ', '2026-11-07', None, 90, '17:00'),
    ('Ngày mai họp nhóm lúc 9h trong 1 tiếng rưỡi', '2026-11-07', '09:00', 90, None),
    ('Ngày kia học Python lúc 14:30 trong 45 phút', '2026-11-08', '14:30', 45, None),
    ('Hôm nay họp lúc 3 giờ chiều trong 30 phút', '2026-11-06', '15:00', 30, None),
    ('Thứ 2 tuần sau học SOA trong 1,5 tiếng', '2026-11-09', None, 90, None),
    ('07/11/2026 học SOA từ 9h đến 10h30', '2026-11-07', '09:00', 90, None),
    ('2026-11-07 học SOA trong 1 giờ 30 phút', '2026-11-07', None, 90, None),
    ('Ngày mai học SOA 90 phút', '2026-11-07', None, 90, None),
    ('Làm bài SOA', None, None, None, None),
])
def test_vietnamese_rules(text, date, start, duration, deadline):
    data = extract_rules(body(text))
    fields = data.fields
    assert (fields.date.isoformat() if fields.date else None) == date
    assert (fields.start_at.strftime('%H:%M') if fields.start_at else None) == start
    assert fields.duration_minutes == duration
    assert (fields.deadline_at.strftime('%H:%M') if fields.deadline_at else None) == deadline
    assert fields.title
    assert 'SOA' in fields.title or fields.title in ('họp nhóm', 'học Python', 'họp')
    assert fields.timezone == 'Asia/Ho_Chi_Minh'


def test_title_preserves_accents_and_does_not_include_time():
    assert extract_rules(body('Ngày mai họp nhóm lúc 9h trong 1 tiếng rưỡi')).fields.title == 'họp nhóm'


def test_reference_crosses_local_midnight():
    data = extract_rules(body('Ngày mai học SOA 30 phút', '2026-11-06T18:00:00Z'))
    assert str(data.fields.date) == '2026-11-08'


@pytest.mark.parametrize('text,code', [
    ('31/02/2027 học SOA lúc 9h', 'INVALID_DATE_TIME'),
    ('Ngày mai học SOA lúc 25h', 'INVALID_DATE_TIME'),
    ('Ngày mai học SOA trong 1500 phút', 'INVALID_DURATION'),
    ('Học SOA lúc 9h', 'DATE_REQUIRED'),
    ('Ngày mai học SOA từ 23h đến 1h', 'AMBIGUOUS_TIME_RANGE'),
    ('Ngày mai học SOA từ 9h đến 10h trong 90 phút', 'DURATION_CONFLICT'),
    ('Ngày mai học SOA lúc 16h trong 90 phút, xong trước 17h', 'DEADLINE_EXCEEDED'),
])
def test_ambiguous_or_invalid_input_returns_warning(text, code):
    result = extract_rules(body(text))
    assert code in [w.code for w in result.warnings]


@pytest.mark.parametrize('failure', ['timeout', 'http', 'json', 'schema'])
def test_provider_fallback(settings, monkeypatch, failure):
    async def broken(*args):
        if failure == 'timeout':
            raise httpx.ReadTimeout('timeout')
        if failure == 'http':
            raise httpx.ConnectError('offline')
        if failure == 'json':
            raise ValueError('bad JSON')
        return ExtractionFields(duration_minutes=0)
    monkeypatch.setattr(LLMClient, 'extract', broken)
    settings.llm_api_key, settings.llm_base_url, settings.llm_model = 'test', 'https://provider.invalid/v1', 'test'
    result = asyncio.run(extract_request(body('Ngày mai học SOA trong 60 phút'), settings, 'trace'))
    assert result.fields.duration_minutes == 60
    assert 'LLM_FALLBACK' in [w.code for w in result.warnings]


def test_llm_http_adapter(settings):
    settings.llm_api_key, settings.llm_base_url, settings.llm_model = 'secret-test', 'https://provider.invalid/v1', 'test'
    def handle(request):
        assert request.headers['Authorization'] == 'Bearer secret-test'
        assert request.headers['X-Request-Id'] == 'trace'
        assert request.url.path == '/v1/chat/completions'
        payload = json.loads(request.content)
        assert payload['model'] == 'test'
        assert 'sourceText' in payload['messages'][1]['content']
        return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps({
            'title': 'Học SOA', 'date': '2026-11-07', 'durationMinutes': 60})}}]})
    result = asyncio.run(LLMClient(settings, httpx.MockTransport(handle)).extract(body('Học SOA'), 'trace'))
    assert result.duration_minutes == 60


def test_internal_endpoint_no_key_and_input_aliases(client, settings):
    response = client.post('/internal/v1/extractions', headers={'X-Internal-Api-Key': settings.internal_api_key},
        json={'prompt': 'Ngày mai học SOA trong 60 phút', 'reference_time': NOW})
    assert response.status_code == 200
    assert response.json()['data']['fields']['title'] == 'học SOA'
