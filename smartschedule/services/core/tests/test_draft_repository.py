from unittest.mock import MagicMock
import pytest
from sqlalchemy.dialects import postgresql
from services.core.models import ScheduleDrafts
from services.core.repositories.drafts import DraftRepository


def test_add_commits_and_refreshes():
    session = MagicMock()
    row = ScheduleDrafts(id='draft')
    assert DraftRepository(session).add(row) is row
    session.add.assert_called_once_with(row)
    session.commit.assert_called_once()
    session.refresh.assert_called_once_with(row)


def test_failed_commit_rolls_back():
    session = MagicMock()
    session.commit.side_effect = RuntimeError('database failure')
    with pytest.raises(RuntimeError):
        DraftRepository(session).add(ScheduleDrafts(id='draft'))
    session.rollback.assert_called_once()
    session.refresh.assert_not_called()


def test_query_filters_id_and_owner():
    session = MagicMock()
    DraftRepository(session).find_owned('draft', 'owner')
    query = session.scalar.call_args.args[0].compile(dialect=postgresql.dialect())
    assert 'schedule_drafts.id =' in str(query)
    assert 'schedule_drafts.user_id =' in str(query)
    assert set(query.params.values()) == {'draft', 'owner'}
