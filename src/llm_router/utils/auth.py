import secrets
import hashlib
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from ..models.api_key import APIKey
from ..schemas import APIKeyRequest, APIKeyResponse


class APIKeyManager:
    """Manages API key creation, validation, and caching."""

    def __init__(self, db: Session, redis_client=None):
        self.db = db
        self.redis = redis_client

    def generate_api_key(self) -> tuple[str, str]:
        """Generate a new API key and its hash."""
        # Get prefix from settings with fallback
        try:
            from ..config import settings

            prefix = getattr(settings, "api_key_prefix", "llm-router-")
        except (ImportError, AttributeError):
            prefix = "llm-router-"  # Fallback if settings not available

        # Generate secure random key
        key = f"{prefix}{secrets.token_urlsafe(32)}"

        # Hash the key for storage
        key_hash = hashlib.sha256(key.encode()).hexdigest()

        return key, key_hash

    def create_api_key(self, request: APIKeyRequest) -> APIKeyResponse:
        """Create a new API key."""
        # Generate key and ID
        key, key_hash = self.generate_api_key()
        key_id = f"ak_{uuid.uuid4().hex[:16]}"

        # Create database record
        api_key = APIKey(
            id=key_id,
            name=request.name,
            description=request.description,
            key_hash=key_hash,
            usage_count=0,
            rate_limit=1000,
            is_active=True,
        )

        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)

        # Cache in Redis if available
        if self.redis:
            try:
                self.redis.setex(
                    f"api_key:{key_hash}",
                    3600,  # 1 hour cache
                    f"{api_key.id}:{api_key.name}:{api_key.is_active}",
                )
            except Exception:
                pass  # Redis is optional

        return APIKeyResponse(
            id=api_key.id,
            name=api_key.name,
            key=key,  # Return the actual key only once
            description=api_key.description,
            created_at=api_key.created_at,
            rate_limit=api_key.rate_limit,
            usage_count=api_key.usage_count,
        )

    def verify_api_key(self, key: str) -> Optional[APIKey]:
        """Verify an API key and return the associated record."""
        key_hash = hashlib.sha256(key.encode()).hexdigest()

        # Try Redis cache first
        if self.redis:
            try:
                cached = self.redis.get(f"api_key:{key_hash}")
                if cached:
                    key_id, name, is_active = cached.split(":", 2)
                    if is_active == "True":
                        # Get full record from database
                        return self.db.query(APIKey).filter(APIKey.id == key_id).first()
            except Exception:
                pass

        # Query database
        api_key = (
            self.db.query(APIKey)
            .filter(APIKey.key_hash == key_hash, APIKey.is_active == True)
            .first()
        )

        if api_key and self.redis:
            # Cache the result
            try:
                self.redis.setex(
                    f"api_key:{key_hash}",
                    3600,
                    f"{api_key.id}:{api_key.name}:{api_key.is_active}",
                )
            except Exception:
                pass

        return api_key

    def increment_usage(self, api_key: APIKey):
        """Increment usage count for an API key."""
        api_key.usage_count += 1
        api_key.last_used_at = datetime.utcnow()
        self.db.commit()

        # Update cache
        if self.redis:
            try:
                key_hash = None  # We'd need to compute this if we want to update cache
                # For now, just let it expire and refresh
                pass
            except Exception:
                pass
