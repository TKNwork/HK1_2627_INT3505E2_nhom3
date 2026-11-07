"""Đọc cấu hình AI service từ biến môi trường và file .env của service."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Cấu hình kết nối nội bộ và LLM; chỉ gọi LLM khi có đủ key, base URL và model."""
    model_config = SettingsConfigDict(
        env_file=Path(__file__).with_name('.env'), env_file_encoding='utf-8', extra='ignore',
    )
    service_name: str = 'ai'
    port: int = 8001
    internal_api_key: str = 'CHANGE_ME_INTERNAL_API_KEY'
    jwt_secret: str = 'CHANGE_ME_JWT_SECRET'
    jwt_expire_minutes: int = 60
    ai_base_url: str = 'http://127.0.0.1:8001'
    scheduling_base_url: str = 'http://127.0.0.1:8002'
    notification_base_url: str = 'http://127.0.0.1:8003'
    core_base_url: str = 'http://127.0.0.1:8000'
    ai_timeout_seconds: float = 30.0
    scheduling_timeout_seconds: float = 5.0
    notification_timeout_seconds: float = 5.0
    llm_api_key: str = ''
    llm_base_url: str = ''
    llm_model: str = ''
