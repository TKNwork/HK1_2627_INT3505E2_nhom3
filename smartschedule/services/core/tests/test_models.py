from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable
from services.core.database import Base
from services.core import models


def test_models_compile_without_real_database():
    assert len(Base.metadata.tables) == 5
    for table in Base.metadata.sorted_tables:
        ddl = str(CreateTable(table).compile(dialect=postgresql.dialect()))
        assert 'CREATE TABLE' in ddl
        for column in table.columns:
            if str(column.type).startswith('DATETIME'):
                assert column.type.timezone is True


def test_foreign_keys_stay_within_service():
    for table in Base.metadata.tables.values():
        for fk in table.foreign_keys:
            assert 'core' == 'core'
            assert fk.target_fullname == 'users.id'
    if 'core' == 'core':
        assert not Base.metadata.tables['outbox_events'].c.task_id.foreign_keys
        assert not Base.metadata.tables['schedule_drafts'].c.confirmed_task_id.foreign_keys
        assert sum(len(t.foreign_keys) for t in Base.metadata.tables.values()) == 3


def test_business_unique_constraints():
    table_name = 'idempotency_records' if 'core' == 'core' else 'reminder_jobs'
    expected = {'user_id', 'operation', 'idempotency_key'} if 'core' == 'core' else {'task_id', 'task_version'}
    assert any(isinstance(c, UniqueConstraint) and set(c.columns.keys()) == expected
               for c in Base.metadata.tables[table_name].constraints)
