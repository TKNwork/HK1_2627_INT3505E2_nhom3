from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import ScheduleDrafts, Users


class DraftRepository:
    def __init__(self, session: Session):
        self.session = session

    def user_exists(self, user_id: str) -> bool:
        return self.session.get(Users, user_id) is not None

    def add(self, draft: ScheduleDrafts) -> ScheduleDrafts:
        """Lưu và đọc lại bản nháp; rollback khi lỗi rồi phát lại ngoại lệ."""
        self.session.add(draft)
        try:
            self.session.commit()
            self.session.refresh(draft)
        except Exception:
            self.session.rollback()
            raise
        return draft

    def find_owned(self, draft_id: str, user_id: str) -> ScheduleDrafts | None:
        """Lọc cả ID bản nháp và user_id; không khớp thì trả None."""
        return self.session.scalar(select(ScheduleDrafts).where(
            ScheduleDrafts.id == draft_id, ScheduleDrafts.user_id == user_id))
