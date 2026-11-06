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
    return DraftRepository(session)


def get_ai_client(request: Request):
    return AIClient(request.app.state.settings)


def draft_response(row: ScheduleDrafts) -> Draft:
    return Draft(id=row.id, source_text=row.source_text, fields=row.fields,
                 missing_fields=row.missing_fields, required_input_fields=row.required_input_fields,
                 warnings=row.warnings, suggestions=row.suggestions, state=row.state,
                 version=row.version, confirmed_task_id=row.confirmed_task_id, expires_at=row.expires_at)


def load_owned_draft(id: str, user: CurrentUser = Depends(get_current_user),
                     repository=Depends(get_draft_repository)):
    row = repository.find_owned(id, user.id)
    if row is None:
        raise AppError(ErrorCode.DRAFT_NOT_FOUND, 404, 'Không tìm thấy bản nháp.')
    if row.expires_at <= datetime.now(timezone.utc):
        raise AppError(ErrorCode.DRAFT_EXPIRED, 410, 'Bản nháp đã hết hạn.')
    return row


async def create_from_text(body: CreateDraft, user_id: str, repository, ai, request_id: str) -> Draft:
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
