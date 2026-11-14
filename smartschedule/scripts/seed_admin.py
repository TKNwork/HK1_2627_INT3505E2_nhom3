"""Thêm hoặc cập nhật tài khoản Admin trực tiếp vào database Core."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.core.config import Settings
from services.core.database import SessionLocal, get_engine
from services.core.models import Base, Users
from services.core.utils.auth import hash_password
from sqlalchemy import text


def seed_admin(email: str, password: str) -> None:
    settings = Settings()
    engine = get_engine(settings.database_url)
    Base.metadata.create_all(engine)

    # Đảm bảo có cột role
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(32) NOT NULL DEFAULT 'user'"))
    except Exception:
        pass

    normalized_email = email.strip().lower()
    session = SessionLocal()
    try:
        user = session.query(Users).filter(Users.email == normalized_email).first()
        if user:
            user.role = 'admin'
            user.password_hash = hash_password(password)
            session.commit()
            print(f"[OK] Da cap nhat tai khoan '{normalized_email}' thanh role ADMIN va doi mat khau thanh cong.")
        else:
            new_admin = Users(
                email=normalized_email,
                password_hash=hash_password(password),
                role='admin',
            )
            session.add(new_admin)
            session.commit()
            print(f"[OK] Da tao tai khoan ADMIN '{normalized_email}' truc tiep vao database thanh cong.")
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description='Them/cap nhat tai khoan Admin vao database.')
    parser.add_argument('--email', default='admin@example.com', help='Email tai khoan admin')
    parser.add_argument('--password', default='AdminPass123', help='Mat khau admin (toi thieu 8 ky tu)')
    args = parser.parse_args()

    seed_admin(args.email, args.password)


if __name__ == '__main__':
    main()

