from unittest.mock import MagicMock
import pytest
from sqlalchemy.dialects import postgresql
from services.core.models import ScheduleDrafts
from services.core.repositories.drafts import DraftRepository


def test_add_flushes_inside_transaction():
    session = MagicMock()
    row = ScheduleDrafts(id='draft')
    assert DraftRepository(session).add(row) is row
    session.add.assert_called_once_with(row)
    session.begin.assert_called_once()
    session.flush.assert_called_once()
    session.begin.return_value.__exit__.assert_called_once_with(None, None, None)
    session.refresh.assert_not_called()


def test_failed_flush_exits_transaction_with_error():
    session = MagicMock()
    session.flush.side_effect = RuntimeError('database failure')
    with pytest.raises(RuntimeError) as error:
        DraftRepository(session).add(ScheduleDrafts(id='draft'))
    assert session.begin.return_value.__exit__.call_args.args[:2] == (RuntimeError, error.value)
    session.refresh.assert_not_called()


def test_query_filters_id_and_owner():
    session = MagicMock()
    DraftRepository(session).find_owned('draft', 'owner')
    query = session.scalar.call_args.args[0].compile(dialect=postgresql.dialect())
    assert 'schedule_drafts.id =' in str(query)
    assert 'schedule_drafts.user_id =' in str(query)
    assert set(query.params.values()) == {'draft', 'owner'}
