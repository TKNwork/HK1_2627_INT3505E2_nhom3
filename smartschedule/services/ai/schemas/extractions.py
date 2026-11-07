"""Schema request, kết quả và cảnh báo của API trích xuất tiếng Việt."""
from datetime import date as Date
from typing import Annotated
from pydantic import AfterValidator, AliasChoices, AwareDatetime, Field, field_validator
from .base import ApiModel, validate_timezone

TimezoneName = Annotated[str, AfterValidator(validate_timezone)]


class ExtractionRequest(ApiModel):
    """Nội dung một công việc, timezone và thời điểm tham chiếu có offset để hiểu ngày tương đối."""
    source_text: str = Field(min_length=1, max_length=2000, validation_alias=AliasChoices('sourceText', 'source_text', 'text', 'prompt'))
    timezone: TimezoneName = 'Asia/Ho_Chi_Minh'
    now: AwareDatetime = Field(validation_alias=AliasChoices('now', 'referenceTime', 'reference_time'))

    @field_validator('source_text')
    @classmethod
    def clean_text(cls, value: str) -> str:
        """Bỏ khoảng trắng ở hai đầu và báo lỗi nếu nội dung chỉ gồm khoảng trắng."""
        if not value.strip():
            raise ValueError('Nội dung không được để trống.')
        return value.strip()


class ExtractionFields(ApiModel):
    """Các giá trị AI trích xuất; thiếu dữ liệu thì để None, thời lượng giới hạn 1–1440 phút."""
    title: str | None = Field(default=None, min_length=1, max_length=200)
    date: Date | None = None
    start_at: AwareDatetime | None = None
    duration_minutes: int | None = Field(default=None, strict=True, ge=1, le=1440)
    deadline_at: AwareDatetime | None = None
    timezone: TimezoneName | None = None
    reminder_minutes: int | None = None


class Warning(ApiModel):
    """Cảnh báo gồm mã để xử lý bằng chương trình và thông báo cho người dùng."""
    code: str
    message: str


class ExtractionData(ApiModel):
    """Kết quả trích xuất gồm fields, trường thiếu, trường cần bổ sung và cảnh báo."""
    fields: ExtractionFields
    missing_fields: list[str]
    required_input_fields: list[str]
    warnings: list[Warning]
