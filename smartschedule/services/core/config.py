from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).with_name('.env'), env_file_encoding='utf-8', extra='ignore',
    )
    service_name: str = 'core'
    port: int = 8000
    database_url: str = 'postgresql+psycopg://core_user:CHANGE_ME_CORE_DB_PASSWORD@127.0.0.1:5433/smartschedule_core'
    init_db: bool = True
    internal_api_key: str = 'CHANGE_ME_INTERNAL_API_KEY'
    jwt_secret: str = 'CHANGE_ME_JWT_SECRET'
    jwt_access_expire_minutes: int = 10
    jwt_refresh_expire_days: int = 7
    ai_base_url: str = 'http://127.0.0.1:8001'
    scheduling_base_url: str = 'http://127.0.0.1:8002'
    notification_base_url: str = 'http://127.0.0.1:8003'
    core_base_url: str = 'http://127.0.0.1:8000'
    ai_timeout_seconds: float = 30.0
    scheduling_timeout_seconds: float = 5.0
    notification_timeout_seconds: float = 5.0

    def require_auth_secrets(self) -> None:
        if self.jwt_secret.startswith('CHANGE_ME') or len(self.jwt_secret) < 32:
            raise RuntimeError('Run python scripts/setup_local.py or configure JWT_SECRET (32+ characters).')
