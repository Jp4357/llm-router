"""API Key model."""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from sqlalchemy.sql import func
from ..database import Base


class APIKey(Base):
    """API Key model for user authentication."""

    __tablename__ = "api_keys"

    id = Column(String, primary_key=True)
    key_hash = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True, nullable=False)
    rate_limit = Column(Integer, default=1000, nullable=False)
    usage_count = Column(Integer, default=0, nullable=False)

    def __repr__(self):
        return f"<APIKey(id='{self.id}', name='{self.name}')>"
