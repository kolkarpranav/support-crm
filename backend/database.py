"""
backend/database.py

Sets up the SQLAlchemy engine, session factory, and declarative Base.
All configuration is pulled from backend.config.Settings (which reads .env).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from backend.config import settings

# ---------------------------------------------------------------------------
# Engine – connects SQLAlchemy to the Supabase PostgreSQL database.
# pool_pre_ping=True ensures stale connections are recycled automatically.
# ---------------------------------------------------------------------------
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

# ---------------------------------------------------------------------------
# SessionLocal – factory that produces new database sessions.
# autocommit=False  → we control transactions explicitly.
# autoflush=False   → we decide when to flush to the DB.
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

# ---------------------------------------------------------------------------
# Base – every ORM model inherits from this so SQLAlchemy tracks the table.
# ---------------------------------------------------------------------------
Base = declarative_base()


# ---------------------------------------------------------------------------
# get_db – FastAPI dependency that yields a DB session per request and
#           guarantees the session is closed afterwards.
# ---------------------------------------------------------------------------
def get_db():
    """Yield a database session for a single request, then close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
