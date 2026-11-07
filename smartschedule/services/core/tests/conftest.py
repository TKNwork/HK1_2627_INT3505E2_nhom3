"""Fixture kiểm thử Core: JWT thật, DB và AI giả để test không cần dịch vụ ngoài."""
import pytest
from fastapi.testclient import TestClient
from services.core.config import Settings
from services.core.main import create_app


@pytest.fixture
def settings() -> Settings:
    """Cung cấp cấu hình test độc lập, không đọc .env và không dùng secret thật."""
    return Settings(_env_file=None, jwt_secret='test-jwt-secret-32-characters-minimum',
                    internal_api_key='test-internal-key-32-characters-minimum')


@pytest.fixture
def app(settings):
    """Tạo app tắt khởi tạo DB; thay get_db, repository và AI client bằng các đối tượng test."""
    from datetime import datetime, timedelta, timezone
    from services.core.models import ScheduleDrafts
    from services.core.services.drafts import get_ai_client, get_draft_repository
    from services.core.services.fixtures import stub_draft
    from services.ai.schemas.extractions import ExtractionRequest
    from services.ai.services.extraction import extract_rules

    class MemoryDrafts:
        """Kho draft trong bộ nhớ chỉ dành cho test; không thay thế repository production."""
        def __init__(self):
            """Chuẩn bị một draft thuộc test-user và còn hạn để kiểm tra các route."""
            draft = stub_draft().model_dump()
            self.rows = {'draft-stub': ScheduleDrafts(**draft, user_id='test-user')}
            self.rows['draft-stub'].expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

        def user_exists(self, user_id):
            """Kiểm tra tài khoản có tồn tại trước khi tiếp tục tạo bản nháp."""
            return user_id in ('test-user', 'other-user')

        def add(self, row):
            """Lưu draft vào kho giả và trả lại row để các test kiểm tra kết quả."""
            self.rows[row.id] = row
            return row

        def find_owned(self, draft_id, user_id):
            """Chỉ trả draft giả khi ID và chủ sở hữu khớp; trường hợp khác trả None."""
            row = self.rows.get(draft_id)
            return row if row is not None and row.user_id == user_id else None

    class LocalAI:
        """AI giả chạy bộ quy tắc trong cùng tiến trình để test không gọi mạng."""
        async def extract(self, payload, request_id):
            """Chạy extract_rules với payload của Core và trả dict theo schema JSON nội bộ."""
            return extract_rules(ExtractionRequest.model_validate(payload)).model_dump(mode='json', by_alias=True)

    app = create_app(settings, init_database_on_startup=False)
    from unittest.mock import MagicMock
    from services.core.database import get_db
    from services.core.models import Users
    app.state.users = {'test-user', 'other-user', 'user-stub'}
    app.state.auth_session = MagicMock()
    app.state.auth_session.get.side_effect = lambda model, user_id: (
        Users(id=user_id) if user_id in app.state.users else None)
    app.dependency_overrides[get_db] = lambda: app.state.auth_session
    app.state.draft_repository = MemoryDrafts()
    app.dependency_overrides[get_draft_repository] = lambda: app.state.draft_repository
    app.dependency_overrides[get_ai_client] = LocalAI
    return app


@pytest.fixture
def client(app):
    """Mở TestClient trong lifespan của app và đóng sau mỗi test."""
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
