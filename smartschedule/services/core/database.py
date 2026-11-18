from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from .config import Settings


class Base(DeclarativeBase):
    pass


@lru_cache(maxsize=4)
def get_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)


def SessionLocal() -> Session:
    settings = Settings()
    return sessionmaker(bind=get_engine(settings.database_url), expire_on_commit=False)()


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


@contextmanager
def transaction(session: Session) -> Iterator[Session]:
    # TODO: chốt ranh giới transaction và khóa chống overlap khi làm nghiệp vụ.
    with session.begin():
        yield session


def init_database(settings: Settings) -> None:
    from . import models  # Register only this service's metadata.
    # TODO: thay create_all bằng Alembic khi bắt đầu quản lý migration.
    engine = get_engine(settings.database_url)
    Base.metadata.create_all(engine)

    # Đảm bảo schema có cột role nếu bảng users đã tồn tại trước đó
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(32) NOT NULL DEFAULT 'user'"))
    except Exception:
        pass

    # Thêm trực tiếp tài khoản admin mặc định vào database nếu chưa có
    try:
        from .utils.auth import hash_password
        with Session(engine) as session:
            admin_email = 'admin@example.com'
            admin = session.query(models.Users).filter(models.Users.email == admin_email).first()
            if not admin:
                any_admin = session.query(models.Users).filter(models.Users.role == 'admin').first()
                if not any_admin:
                    new_admin = models.Users(
                        email=admin_email,
                        password_hash=hash_password('AdminPass123'),
                        role='admin',
                    )
                    session.add(new_admin)
                    session.commit()
    except Exception:
        pass
