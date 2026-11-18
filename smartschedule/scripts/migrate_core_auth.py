"""Upgrade the Core refresh-token schema before deploying the Auth routes."""

from sqlalchemy import text
from sqlalchemy.engine import Engine

from services.core.config import Settings
from services.core.database import get_engine
from services.core.models import RefreshTokens


def migrate(engine: Engine) -> None:
    if engine.dialect.name != 'postgresql':
        raise ValueError('Core Auth migration requires PostgreSQL.')
    with engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(hashtext('smartschedule:core:refresh_tokens'))"))
        RefreshTokens.__table__.create(connection, checkfirst=True)
        connection.execute(text('ALTER TABLE refresh_tokens ADD COLUMN IF NOT EXISTS session_id VARCHAR(128)'))
        connection.execute(text('UPDATE refresh_tokens SET session_id = id WHERE session_id IS NULL'))
        connection.execute(text('ALTER TABLE refresh_tokens ALTER COLUMN session_id SET NOT NULL'))
        connection.execute(text('CREATE INDEX IF NOT EXISTS ix_refresh_tokens_session ON refresh_tokens (session_id)'))


if __name__ == '__main__':
    migrate(get_engine(Settings().database_url))
    print('Core refresh_tokens schema is ready.')
