"""Start four local Uvicorn processes, check their contracts, then stop those processes."""
import argparse
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import httpx
from sqlalchemy import inspect
from sqlalchemy.engine import make_url

from services.core.config import Settings as CoreSettings
from services.notification.config import Settings as NotificationSettings
from scripts.check_contract import contract_endpoints

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core-port', type=int, default=8000)
    parser.add_argument('--ai-port', type=int, default=8001)
    parser.add_argument('--scheduling-port', type=int, default=8002)
    parser.add_argument('--notification-port', type=int, default=8003)
    parser.add_argument('--core-db-port', type=int, default=5433)
    args = parser.parse_args()
    ports = {name: getattr(args, name + '_port') for name in ('core', 'ai', 'scheduling', 'notification')}
    local = ROOT / '.local'
    local.mkdir(exist_ok=True)
    children: list[subprocess.Popen] = []
    logs = []
    report: dict = {'ports': ports, 'coreDbPort': args.core_db_port, 'services': {}, 'routes': []}
    core_settings = CoreSettings()
    core_url = make_url(core_settings.database_url).set(port=args.core_db_port).render_as_string(hide_password=False)
    try:
        for name, port in ports.items():
            env = os.environ.copy()
            if name == 'core':
                env['DATABASE_URL'] = core_url
            # Explicitly test schema creation on the two real PostgreSQL instances.
            if name in ('core', 'notification'):
                env['INIT_DB'] = 'true'
            log = (local / f'smoke-{name}.log').open('w', encoding='utf-8')
            logs.append(log)
            children.append(subprocess.Popen(
                [sys.executable, '-m', 'uvicorn', f'services.{name}.main:app',
                 '--host', '127.0.0.1', '--port', str(port)],
                cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            ))
        with httpx.Client(timeout=5, trust_env=False) as client:
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
            # Exercise every endpoint over real HTTP using the same representative fixtures as unit tests.
            from services.core.tests.test_routes import ROUTES
            login = client.post(f'http://127.0.0.1:{ports["core"]}/api/v1/auth/login',
                                json={'email': 'demo@example.com', 'password': 'DemoPass123'})
            login.raise_for_status()
            headers = {'Authorization': 'Bearer ' + login.json()['data']['accessToken'],
                       'Idempotency-Key': 'live-smoke-confirm', 'X-Request-Id': 'live-smoke'}
            for method, path, body, expected in ROUTES:
                response = client.request(method, f'http://127.0.0.1:{ports["core"]}' + path,
                                          json=body, headers=headers)
                assert response.status_code == expected, f'{method} {path}: {response.status_code}'
                if expected == 204:
                    assert response.content == b''
                else:
                    assert response.json()['requestId'] == 'live-smoke'
                report['routes'].append({'service': 'core', 'method': method.upper(), 'path': path, 'status': expected})
            for name in ('ai', 'scheduling', 'notification'):
                module = importlib.import_module(f'services.{name}.tests.test_routes')
                settings = importlib.import_module(f'services.{name}.config').Settings()
                internal_headers = {'X-Internal-Api-Key': settings.internal_api_key, 'X-Request-Id': 'live-smoke'}
                for method, path, body, expected in module.CASES:
                    response = client.request(method, f'http://127.0.0.1:{ports[name]}' + path,
                                              json=body, headers=internal_headers)
                    assert response.status_code == expected, f'{name} {path}: {response.status_code}'
                    assert response.json()['requestId'] == 'live-smoke'
                    report['routes'].append({'service': name, 'method': method.upper(), 'path': path, 'status': expected})
            assert len(report['routes']) == len(contract_endpoints()) == 22
        for name in ('core', 'notification'):
            database = importlib.import_module(f'services.{name}.database')
            importlib.import_module(f'services.{name}.models')
            url = core_url if name == 'core' else NotificationSettings().database_url
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
        print('PASS: 4 Uvicorn processes, health/Swagger, all 22 endpoints, 2 real DB schemas.')
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
