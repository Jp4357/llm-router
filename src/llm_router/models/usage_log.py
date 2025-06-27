from sqlalchemy import Column, String, Integer, Float, DateTime, Text
from sqlalchemy.sql import func
from ..database import Base


class UsageLog(Base):
    """Usage log model for tracking API usage."""

    __tablename__ = "usage_logs"

    id = Column(String, primary_key=True)
    api_key_id = Column(String, nullable=False, index=True)

    # Request details
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    endpoint = Column(String, nullable=False)

    # Usage metrics
    tokens_used = Column(Integer, default=0)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    cost = Column(Float, default=0.0)

    # Request metadata (JSON as text)
    request_data = Column(Text)  # Avoiding 'metadata' as it's reserved

    # Timestamps
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<UsageLog(id='{self.id}', provider='{self.provider}', model='{self.model}')>"

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "api_key_id": self.api_key_id,
            "provider": self.provider,
            "model": self.model,
            "endpoint": self.endpoint,
            "tokens_used": self.tokens_used,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cost": self.cost,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
