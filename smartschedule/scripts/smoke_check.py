"""Start four local Uvicorn processes, check their contracts, then stop those processes."""
import argparse
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone
from uuid import UUID, uuid4

import httpx
from sqlalchemy import inspect
from sqlalchemy.engine import make_url

from services.core.config import Settings as CoreSettings
from services.notification.config import Settings as NotificationSettings
from scripts.check_contract import contract_endpoints

ROOT = Path(__file__).resolve().parents[1]


def check_core(client, base, send):
    credentials = {'email': f'smoke-{uuid4().hex}@example.com', 'password': uuid4().hex}
    headers = {'X-Request-Id': 'live-smoke'}

    def request(method, path, body, expected):
        return send('core', method, path, body, expected, headers)

    request('post', '/api/v1/auth/register', credentials, 201)
    tokens = request('post', '/api/v1/auth/login', credentials, 200)
    headers['Authorization'] = 'Bearer ' + tokens['accessToken']
    zone = 'Asia/Ho_Chi_Minh'
    task = request('post', '/api/v1/tasks', {
        'title': 'Smoke check', 'durationMinutes': 60, 'timezone': zone,
    }, 201)['task']
    task_path = f'/api/v1/tasks/{task["id"]}'
    request('get', '/api/v1/tasks?limit=20', None, 200)
    task = request('get', task_path, None, 200)['task']
    task = request('patch', task_path, {'expectedVersion': task['version'], 'title': 'Updated'}, 200)['task']
    task = request('post', task_path + '/complete', {'expectedVersion': task['version']}, 200)['task']
    request('delete', f'{task_path}?expectedVersion={task["version"]}', None, 204)

    draft = request('post', '/api/v1/schedule-drafts', {
        'sourceText': 'Ngày mai họp nhóm lúc 9h trong 60 phút', 'timezone': zone,
    }, 201)['draft']
    assert UUID(draft['id']).version == 4
    assert datetime.fromisoformat(draft['expiresAt']) > datetime.now(timezone.utc)
    assert draft['fields']['durationMinutes'] == 60 and draft['state'] == 'ready_to_confirm'
    draft_path = f'/api/v1/schedule-drafts/{draft["id"]}'
    assert request('get', draft_path, None, 200)['draft'] == draft
    headers['Idempotency-Key'] = uuid4().hex
    version = {'expectedVersion': draft['version']}
    request('patch', draft_path, {**version, 'fields': {'durationMinutes': 90}}, 501)
    request('post', draft_path + '/suggestions', version, 501)
    request('post', draft_path + '/confirm', version, 501)
    assert client.get(base + draft_path, headers=headers).json()['data']['draft'] == draft
    request('get', f'/api/v1/calendar?date=2030-11-02&timezone={zone}', None, 200)
    request('post', '/api/v1/telegram/link-codes', None, 201)
    request('get', '/api/v1/telegram/link', None, 200)

    refresh_url = base + '/api/v1/auth/refresh'
    first_refresh = {'refreshToken': tokens['refreshToken']}
    rotated = client.post(refresh_url, json=first_refresh)
    assert rotated.status_code == 200, rotated.text
    assert client.post(base + '/api/v1/auth/logout', json=first_refresh).status_code == 204
    next_refresh = {'refreshToken': rotated.json()['data']['refreshToken']}
    denied = client.post(refresh_url, json=next_refresh)
    assert denied.status_code == 401 and denied.json()['error']['code'] == 'UNAUTHORIZED'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core-port', type=int, default=8000)
    parser.add_argument('--ai-port', type=int, default=8001)
    parser.add_argument('--scheduling-port', type=int, default=8002)
    parser.add_argument('--notification-port', type=int, default=8003)
    parser.add_argument('--core-db-port', type=int, default=5433)
    parser.add_argument('--notification-db-port', type=int, default=5434)
    args = parser.parse_args()
    ports = {name: getattr(args, name + '_port') for name in ('core', 'ai', 'scheduling', 'notification')}
    local = ROOT / '.local'
    local.mkdir(exist_ok=True)
    children: list[subprocess.Popen] = []
    logs = []
    report: dict = {'ports': ports, 'coreDbPort': args.core_db_port, 'services': {}, 'routes': []}
    core_settings = CoreSettings()
    core_url = make_url(core_settings.database_url).set(port=args.core_db_port).render_as_string(hide_password=False)
    notification_url = make_url(NotificationSettings().database_url).set(
        port=args.notification_db_port,
    ).render_as_string(hide_password=False)
    database_urls = {'core': core_url, 'notification': notification_url}
    try:
        for name, port in ports.items():
            env = os.environ.copy()
            if name == 'core':
                env['AI_BASE_URL'] = f'http://127.0.0.1:{ports["ai"]}'
            if name == 'ai':
                env['LLM_API_KEY'] = ''
            # Explicitly test schema creation on the two real PostgreSQL instances.
            if name in database_urls:
                env['INIT_DB'] = 'true'
                env['DATABASE_URL'] = database_urls[name]
            log = (local / f'smoke-{name}.log').open('w', encoding='utf-8')
            logs.append(log)
            children.append(subprocess.Popen(
                [sys.executable, '-m', 'uvicorn', f'services.{name}.main:app',
                 '--host', '127.0.0.1', '--port', str(port)],
                cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            ))
        with httpx.Client(timeout=max(5, core_settings.ai_timeout_seconds + 5), trust_env=False) as client:
            for (name, port), process in zip(ports.items(), children):
                base = f'http://127.0.0.1:{port}'
                deadline = time.monotonic() + 45
                while True:
                    if process.poll() is not None:
                        raise RuntimeError(f'{name} exited. Inspect .local/smoke-{name}.log (may be a port conflict).')
                    try:
                        health = client.get(base + '/health', headers={'X-Request-Id': 'live-smoke'})
                        if health.status_code == 200:
                            assert health.json()['data']['service'] == name
                            assert health.headers['X-Request-Id'] == health.json()['requestId'] == 'live-smoke'
                            break
                    except httpx.TransportError:
                        pass
                    if time.monotonic() >= deadline:
                        raise RuntimeError(f'{name} startup timed out; see .local/smoke-{name}.log')
                    time.sleep(0.2)
                assert client.get(base + '/docs').status_code == 200
                spec = client.get(base + '/openapi.json').json()
                operations = {op['operationId']: (method.upper(), path)
                              for path, methods in spec['paths'].items()
                              for method, op in methods.items()
                              if op.get('operationId', '').startswith(('API-', 'INT-'))}
                report['services'][name] = {'health': 200, 'swagger': 200, 'operationIds': sorted(operations)}
                print(f'{name}: health=200, Swagger=200, endpoints={len(operations)}')
            def send(name, method, path, body, expected, headers):
                response = client.request(method, f'http://127.0.0.1:{ports[name]}' + path,
                                          json=body, headers=headers)
                assert response.status_code == expected, f'{method} {path}: {response.status_code} {response.text}'
                report['routes'].append({'service': name, 'method': method.upper(), 'path': path, 'status': expected})
                if expected == 204:
                    assert response.content == b''
                    return None
                payload = response.json()
                assert payload['requestId'] == 'live-smoke'
                if expected == 501:
                    assert payload['error']['code'] == 'NOT_IMPLEMENTED'
                return payload.get('data')

            check_core(client, f'http://127.0.0.1:{ports["core"]}', send)
            for name in ('ai', 'scheduling', 'notification'):
                module = importlib.import_module(f'services.{name}.tests.test_routes')
                settings = importlib.import_module(f'services.{name}.config').Settings()
                internal_headers = {'X-Internal-Api-Key': settings.internal_api_key, 'X-Request-Id': 'live-smoke'}
                for method, path, body, expected in module.CASES:
                    send(name, method, path, body, expected, internal_headers)
            assert len(report['routes']) == len(contract_endpoints()) == 22
        for name in ('core', 'notification'):
            database = importlib.import_module(f'services.{name}.database')
            importlib.import_module(f'services.{name}.models')
            url = database_urls[name]
            inspector = inspect(database.get_engine(url))
            actual = set(inspector.get_table_names())
            expected_tables = set(database.Base.metadata.tables)
            assert actual == expected_tables
            for table in database.Base.metadata.tables.values():
                actual_columns = {column['name'] for column in inspector.get_columns(table.name)}
                assert actual_columns == set(table.columns.keys())
            report['services'][name]['databaseTables'] = sorted(actual)
            print(f'{name}: real PostgreSQL schema verified ({len(actual)} tables).')
        (local / 'smoke-results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print('PASS: 4 Uvicorn processes, 22 routes (3 draft stubs), Auth rotation/logout, 2 PostgreSQL schemas.')
    finally:
        for process in children:
            if process.poll() is None:
                process.terminate()
        for process in children:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for log in logs:
            log.close()


if __name__ == '__main__':
    main()
