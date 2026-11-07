"""DTO đầu vào, đầu ra và dữ liệu trích xuất dùng trong các API bản nháp."""
from datetime import date as Date
from typing import Literal
from pydantic import AliasChoices, AwareDatetime, Field, field_validator
from .base import ApiModel
from .tasks import Duration, ReminderMinutes, TimezoneName, Title, Version, Task


class Warning(ApiModel):
    """Cảnh báo gồm mã để xử lý bằng chương trình và thông báo cho người dùng."""
    code: str
    message: str


class Slot(ApiModel):
    """Khoảng thời gian gợi ý có giờ bắt đầu và kết thúc kèm múi giờ."""
    start_at: AwareDatetime
    end_at: AwareDatetime


class DraftFields(ApiModel):
    """Các trường đang có trong bản nháp; giá trị chưa xác định có thể là None."""
    title: Title | None = None
    date: Date | None = None
    start_at: AwareDatetime | None = None
    duration_minutes: Duration | None = None
    deadline_at: AwareDatetime | None = None
    timezone: TimezoneName | None = None
    reminder_minutes: ReminderMinutes | None = None


class ExtractionResult(ApiModel):
    """Schema Core dùng để kiểm tra fields, trường thiếu và cảnh báo do AI trả về."""
    fields: DraftFields
    missing_fields: list[str]
    required_input_fields: list[str]
    warnings: list[Warning]


class Draft(ApiModel):
    """Dữ liệu public của bản nháp gồm nội dung, trạng thái, phiên bản và hạn sử dụng."""
    id: str
    source_text: str
    fields: DraftFields
    missing_fields: list[str]
    required_input_fields: list[str]
    warnings: list[Warning]
    suggestions: list[Slot]
    state: Literal['needs_input', 'ready_to_schedule', 'ready_to_confirm', 'confirmed']
    version: Version
    confirmed_task_id: str | None
    expires_at: AwareDatetime


class CreateDraft(ApiModel):
    """Đầu vào UC-09; hỗ trợ alias nội dung, timezone mặc định và reference_time có offset."""
    source_text: str = Field(min_length=1, max_length=2000, validation_alias=AliasChoices('sourceText', 'source_text', 'text', 'prompt'))
    timezone: TimezoneName = 'Asia/Ho_Chi_Minh'
    reference_time: AwareDatetime | None = Field(default=None, validation_alias=AliasChoices('referenceTime', 'reference_time'))

    @field_validator('source_text')
    @classmethod
    def clean_text(cls, value: str) -> str:
        """Bỏ khoảng trắng ở hai đầu và báo lỗi nếu nội dung chỉ gồm khoảng trắng."""
        if not value.strip():
            raise ValueError('Nội dung không được để trống.')
        return value.strip()


class PatchDraft(ApiModel):
    """Đầu vào dự kiến khi sửa draft, gồm phiên bản mong đợi và các trường thay đổi."""
    expected_version: Version
    fields: DraftFields


class SuggestDraft(ApiModel):
    """Đầu vào dự kiến khi tìm giờ: phiên bản, phạm vi tìm và số gợi ý tối đa."""
    expected_version: Version
    search_from: AwareDatetime | None = None
    search_to: AwareDatetime | None = None
    max_results: int = Field(default=3, ge=1, le=3)


class DraftData(ApiModel):
    """Phần data của response chứa một bản nháp."""
    draft: Draft


class SuggestionsData(DraftData):
    """Response bản nháp kèm thông báo cho bước tìm giờ đề xuất."""
    notice: str


class ConfirmData(DraftData):
    """Response dự kiến của bước xác nhận, chứa task và bản nháp liên quan."""
    task: Task
