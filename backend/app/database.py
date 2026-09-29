"""
Database setup for the Inbox-to-Action Butler.

- Local / Docker / Render: SQLite file in app/data (persistent on disk).
- Vercel: the deployment filesystem is read-only except /tmp, so SQLite is
  placed there. /tmp is EPHEMERAL (cleared on cold starts, not shared between
  instances) - fine for a demo, not for real data.
- Any environment: set DATABASE_URL (e.g. a Neon/Supabase Postgres URL) to use
  a real database instead. No other code changes needed.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

ON_VERCEL = bool(os.environ.get("VERCEL"))
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

if DATABASE_URL:
    # Some providers hand out "postgres://", which SQLAlchemy 2.x rejects.
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
else:
    if ON_VERCEL:
        DATA_DIR = "/tmp"
    else:
        DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(DATA_DIR, exist_ok=True)
    DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'butler.db')}"

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()