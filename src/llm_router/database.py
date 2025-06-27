from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import redis
import logging

from .config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy setup
engine = create_engine(
    settings.database_url,
    connect_args=(
        {"check_same_thread": False} if "sqlite" in settings.database_url else {}
    ),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis setup (optional)
redis_client = None
try:
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    redis_client.ping()  # Test connection
    logger.info("✅ Redis connected successfully")
except Exception as e:
    logger.warning(f"⚠️ Redis not available: {e}")
    redis_client = None


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_redis():
    """Get Redis client (optional)."""
    return redis_client


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables created")
