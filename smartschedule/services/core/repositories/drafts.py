from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import ScheduleDrafts, Users


class DraftRepository:
    def __init__(self, session: Session):
        self.session = session

    def user_exists(self, user_id: str) -> bool:
        with self.session.begin():
            return self.session.scalar(select(Users.id).where(Users.id == user_id)) is not None

    def add(self, draft: ScheduleDrafts) -> ScheduleDrafts:
        """Lưu bản nháp trong một transaction."""
        with self.session.begin():
            self.session.add(draft)
            self.session.flush()
        return draft

    def find_owned(self, draft_id: str, user_id: str) -> ScheduleDrafts | None:
        """Lọc cả ID bản nháp và user_id; không khớp thì trả None."""
        return self.session.scalar(select(ScheduleDrafts).where(
            ScheduleDrafts.id == draft_id, ScheduleDrafts.user_id == user_id))
