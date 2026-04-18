from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker

from src.core.config.settings import settings
from src.core.constants import DB_DIALECT, DB_DRIVER, DB_MAX_OVERFLOW, DB_POOL_SIZE


def _build_url() -> URL:
    return URL.create(
        drivername=f"{DB_DIALECT}+{DB_DRIVER}",
        username=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database=settings.DB_NAME,
    )


engine = create_engine(
    _build_url(),
    pool_pre_ping=True,     # detect stale connections
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema_initialized() -> None:
    """
    Ensure database schema is initialized on application startup.
    
    This validates that the cv_sessions table exists with the expected structure.
    If validation fails, the application will fail to start.
    """
    from src.domain.session.migration_guard import SessionSchemaMigrationGuard
    
    db = SessionLocal()
    try:
        SessionSchemaMigrationGuard.ensure_schema_initialized(db)
    finally:
        db.close()
