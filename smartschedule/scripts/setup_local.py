"""Create missing local .env files with random development credentials."""
from pathlib import Path
import secrets

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    root_env = ROOT / '.env'
    if not root_env.exists():
        text = (ROOT / '.env.example').read_text(encoding='utf-8')
        for name in ('CORE_DB_PASSWORD', 'NOTIFICATION_DB_PASSWORD', 'JWT_SECRET', 'INTERNAL_API_KEY'):
            text = text.replace('CHANGE_ME_' + name, secrets.token_hex(32))
        root_env.write_text(text, encoding='utf-8')
    values = {}
    for line in root_env.read_text(encoding='utf-8').splitlines():
        if line.strip() and not line.lstrip().startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            values[key.strip()] = value.strip()
    for service in ('core', 'ai', 'scheduling', 'notification'):
        target = ROOT / 'services' / service / '.env'
        if target.exists():
            print(f'Keep existing: services/{service}/.env')
            continue
        text = target.with_name('.env.example').read_text(encoding='utf-8')
        for key, value in values.items():
            text = text.replace('CHANGE_ME_' + key, value)
        target.write_text(text, encoding='utf-8')
        print(f'Created: services/{service}/.env')
    print('Local settings ready. Existing files and database volumes were not modified.')


if __name__ == '__main__':
    main()
