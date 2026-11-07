"""Điều phối UC-09: gọi AI, kiểm tra dữ liệu và lưu bản nháp trong Core."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo
from fastapi import Depends, Request
from pydantic import ValidationError
from ..clients.ai_client import AIClient
from ..database import get_db
from ..models import ScheduleDrafts
from ..repositories.drafts import DraftRepository
from ..schemas.drafts import CreateDraft, Draft, ExtractionResult
from ..utils.auth import CurrentUser, get_current_user
from ..utils.errors import AppError, ErrorCode


def get_draft_repository(session=Depends(get_db)):
    """Cung cấp repository dùng phiên DB của request qua dependency FastAPI."""
    return DraftRepository(session)


def get_ai_client(request: Request):
    """Tạo client gọi AI từ cấu hình của ứng dụng Core."""
    return AIClient(request.app.state.settings)


def draft_response(row: ScheduleDrafts) -> Draft:
    """Chuyển bản ghi ScheduleDrafts thành DTO Draft để kiểm tra và trả qua API."""
    return Draft(id=row.id, source_text=row.source_text, fields=row.fields,
                 missing_fields=row.missing_fields, required_input_fields=row.required_input_fields,
                 warnings=row.warnings, suggestions=row.suggestions, state=row.state,
                 version=row.version, confirmed_task_id=row.confirmed_task_id, expires_at=row.expires_at)


def load_owned_draft(id: str, user: CurrentUser = Depends(get_current_user),
                     repository=Depends(get_draft_repository)):
    """Lấy bản nháp còn hạn thuộc người dùng trong JWT.

    Hàm được dùng làm dependency cho các route bản nháp. Repository lọc đồng thời
    id và user.id; không tìm thấy hoặc khác chủ sở hữu đều trả 404. Bản nháp thuộc
    người dùng nhưng đã hết hạn trả 410. Hàm không gia hạn hoặc sửa bản nháp."""
    row = repository.find_owned(id, user.id)
    if row is None:
        raise AppError(ErrorCode.DRAFT_NOT_FOUND, 404, 'Không tìm thấy bản nháp.')
    if row.expires_at <= datetime.now(timezone.utc):
        raise AppError(ErrorCode.DRAFT_EXPIRED, 410, 'Bản nháp đã hết hạn.')
    return row


async def create_from_text(body: CreateDraft, user_id: str, repository, ai, request_id: str) -> Draft:
    """Tạo bản nháp từ câu tiếng Việt cho user_id đã được xác thực.

    body chứa nội dung, múi giờ và thời điểm tham chiếu tùy chọn. Hàm gọi ai.extract
    bằng request_id hiện tại, kiểm schema, chuẩn hóa thời điểm sang UTC rồi tính lại
    trường thiếu và trạng thái trước khi repository lưu dữ liệu.

    Kết quả là DTO Draft có version 1 và hạn dùng 30 phút tính từ giờ máy chủ lấy
    trước lời gọi AI. reference_time chỉ dùng để diễn giải câu, không quyết định TTL.
    Không tạo task, gợi ý lịch hoặc sự kiện nhắc việc.

    Báo 401 nếu user không tồn tại, 502 nếu kết quả AI sai; lỗi 503/504 từ client AI
    được truyền lên tầng xử lý lỗi chung. Lỗi DB được repository rollback khi có thể
    rồi truyền lên, không đổi thành lỗi AI."""
    if not repository.user_exists(user_id):
        raise AppError(ErrorCode.UNAUTHORIZED, 401, 'Tài khoản không tồn tại.')
    now = datetime.now(timezone.utc)
    reference = body.reference_time or now
    payload = {'sourceText': body.source_text, 'timezone': body.timezone, 'now': reference.isoformat()}
    result = await ai.extract(payload, request_id)
    try:
        extraction = ExtractionResult.model_validate(result)
        fields = extraction.fields
        fields.timezone = body.timezone
        if fields.title is not None:
            fields.title = fields.title.strip()
            if not fields.title:
                raise ValueError('Tiêu đề trống')
        if fields.start_at:
            local_date = fields.start_at.astimezone(ZoneInfo(body.timezone)).date()
            if fields.date and fields.date != local_date:
                raise ValueError('Ngày và giờ không khớp')
            fields.date = local_date
            fields.start_at = fields.start_at.astimezone(timezone.utc)
        if fields.deadline_at:
            fields.deadline_at = fields.deadline_at.astimezone(timezone.utc)
        missing = [alias for name, alias in [('title', 'title'), ('date', 'date'),
            ('start_at', 'startAt'), ('duration_minutes', 'durationMinutes')] if getattr(fields, name) is None]
        required = [name for name in missing if name in ('title', 'durationMinutes')]
        if fields.date is None and fields.start_at is None and fields.deadline_at is None:
            required.append('date')
        # Core tính lại trạng thái, không tin state/missingFields từ dịch vụ phụ thuộc.
        state = 'needs_input' if required else ('ready_to_confirm' if fields.start_at else 'ready_to_schedule')
        warnings = [warning.model_dump() for warning in extraction.warnings]
        if fields.start_at and fields.duration_minutes and fields.deadline_at:
            if fields.start_at + timedelta(minutes=fields.duration_minutes) > fields.deadline_at:
                state = 'needs_input'
                required.append('deadlineAt')
                if not any(warning['code'] == 'DEADLINE_EXCEEDED' for warning in warnings):
                    warnings.append({'code': 'DEADLINE_EXCEEDED', 'message': 'Thời gian kết thúc vượt deadline.'})
        row = ScheduleDrafts(id=str(uuid4()), user_id=user_id, source_text=body.source_text,
            fields=fields.model_dump(mode='json', by_alias=True), missing_fields=missing,
            required_input_fields=required, warnings=warnings, suggestions=[], state=state,
            version=1, confirmed_task_id=None, expires_at=now + timedelta(minutes=30))
        draft_response(row)
    except (ValidationError, ValueError, KeyError, TypeError) as exc:
        raise AppError(ErrorCode.AI_INVALID_RESPONSE, 502, 'Kết quả AI không hợp lệ.') from exc
    return draft_response(repository.add(row))
