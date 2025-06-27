import jwt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from ..models.api_key import APIKey
from ..config import settings


class TokenManager:
    """Manages JWT tokens for authentication."""

    def __init__(self, db: Session):
        self.db = db
        self.secret_key = settings.secret_key
        self.algorithm = "HS256"
        self.default_expiry = timedelta(hours=24)  # 24 hours default

    def create_token(
        self, api_key_id: str, expires_in: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """Create a JWT token for an API key."""
        if expires_in is None:
            expires_in = self.default_expiry

        # Get API key details
        api_key = self.db.query(APIKey).filter(APIKey.id == api_key_id).first()
        if not api_key or not api_key.is_active:
            raise ValueError("Invalid or inactive API key")

        # Create token payload
        now = datetime.utcnow()
        expiry = now + expires_in

        payload = {
            "sub": api_key_id,  # Subject (API key ID)
            "name": api_key.name,  # API key name
            "iat": now,  # Issued at
            "exp": expiry,  # Expires at
            "jti": secrets.token_hex(16),  # JWT ID (unique identifier)
            "type": "access",  # Token type
        }

        # Create JWT token
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": int(expires_in.total_seconds()),
            "expires_at": expiry.isoformat(),
            "api_key_id": api_key_id,
            "api_key_name": api_key.name,
        }

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token."""
        try:
            # Decode the token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Check if token has expired (jwt library does this automatically)
            api_key_id = payload.get("sub")
            if not api_key_id:
                return None

            # Verify the API key still exists and is active
            api_key = (
                self.db.query(APIKey)
                .filter(APIKey.id == api_key_id, APIKey.is_active == True)
                .first()
            )

            if not api_key:
                return None

            return {
                "api_key_id": api_key_id,
                "api_key_name": payload.get("name"),
                "token_id": payload.get("jti"),
                "issued_at": payload.get("iat"),
                "expires_at": payload.get("exp"),
                "api_key_record": api_key,
            }

        except jwt.ExpiredSignatureError:
            return None  # Token expired
        except jwt.InvalidTokenError:
            return None  # Invalid token
        except Exception:
            return None  # Other errors

    def refresh_token(self, old_token: str) -> Optional[Dict[str, Any]]:
        """Refresh an existing token (create a new one)."""
        token_data = self.verify_token(old_token)
        if not token_data:
            return None

        # Create a new token for the same API key
        return self.create_token(token_data["api_key_id"])

    def revoke_token(self, token: str) -> bool:
        """Revoke a token (for now, just verify it's valid)."""
        # In a more sophisticated system, you'd maintain a blacklist
        # For now, we just verify the token exists
        return self.verify_token(token) is not None
