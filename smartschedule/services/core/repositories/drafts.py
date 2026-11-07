"""Truy cập bảng users và schedule_drafts trong database của Core."""
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import ScheduleDrafts, Users


class DraftRepository:
    """Gom thao tác lưu và tìm bản nháp theo chủ sở hữu trên một SQLAlchemy Session."""
    def __init__(self, session: Session):
        """Nhận phiên DB do dependency cung cấp; không tự tạo hoặc đóng phiên."""
        self.session = session

    def user_exists(self, user_id: str) -> bool:
        """Kiểm tra tài khoản có tồn tại trước khi tiếp tục tạo bản nháp."""
        return self.session.get(Users, user_id) is not None

    def add(self, draft: ScheduleDrafts) -> ScheduleDrafts:
        """Lưu draft, commit rồi refresh và trả lại bản ghi.

        Nếu commit hoặc refresh phát sinh lỗi, gọi rollback rồi phát lại lỗi gốc.
        Rollback không hoàn tác được transaction đã commit trước lỗi refresh."""
        self.session.add(draft)
        try:
            self.session.commit()
            self.session.refresh(draft)
        except Exception:
            self.session.rollback()
            raise
        return draft

    def find_owned(self, draft_id: str, user_id: str) -> ScheduleDrafts | None:
        """Tìm bằng cả draft_id và user_id, trả None nếu không có bản ghi khớp.

        Điều kiện chủ sở hữu phải nằm trong truy vấn để tránh đọc draft của user khác.
        Việc kiểm tra hạn sử dụng và chuyển thành lỗi HTTP nằm ở load_owned_draft."""
        return self.session.scalar(select(ScheduleDrafts).where(
            ScheduleDrafts.id == draft_id, ScheduleDrafts.user_id == user_id))
