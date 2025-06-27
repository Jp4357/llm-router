from fastapi import Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db, get_redis
from ..models.api_key import APIKey
from ..utils.auth import APIKeyManager


from fastapi import Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db, get_redis
from ..models.api_key import APIKey
from ..utils.auth import APIKeyManager


async def verify_api_key(
    request: Request,
    authorization: Optional[str] = Header(None),
    api_key: Optional[str] = Header(None, alias="x-api-key"),
    db: Session = Depends(get_db),
) -> APIKey:
    """Verify API key from Authorization header with multiple fallback methods."""

    # Method 1: Try the authorization parameter
    auth_header = authorization

    # Method 2: Try custom x-api-key header
    if not auth_header and api_key:
        auth_header = (
            api_key if api_key.startswith("llm-router-") else f"Bearer {api_key}"
        )

    # Method 3: Try getting from request headers directly
    if not auth_header:
        auth_header = request.headers.get("authorization")

    # Method 4: Try case variations
    if not auth_header:
        auth_header = request.headers.get("Authorization")

    # Method 5: Try custom header variations
    if not auth_header:
        auth_header = request.headers.get("x-api-key")

    # Debug all headers (comment out in production)
    print(f"🔍 All request headers: {dict(request.headers)}")
    print(f"🔍 Authorization parameter: {authorization}")
    print(f"🔍 X-API-Key parameter: {api_key}")
    print(f"🔍 Final auth_header: {auth_header}")

    if not auth_header:
        print("❌ No authorization header found in any method")
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Missing authorization header",
                "message": "Add one of these headers:",
                "options": [
                    "Authorization: Bearer llm-router-your-key",
                    "x-api-key: llm-router-your-key",
                ],
                "debug_headers": dict(request.headers),
            },
        )

    # Handle different authorization formats
    api_key_value = None

    if auth_header.startswith("Bearer "):
        # Standard format: "Bearer llm-router-..."
        api_key_value = auth_header.replace("Bearer ", "").strip()
    elif auth_header.startswith("llm-router-"):
        # Direct format: "llm-router-..."
        api_key_value = auth_header.strip()
    else:
        # Try to extract the key if it contains our prefix
        if "llm-router-" in auth_header:
            start_idx = auth_header.find("llm-router-")
            api_key_value = auth_header[start_idx:].strip()

    print(f"🔍 Extracted API key: {api_key_value[:20] if api_key_value else 'None'}...")

    if not api_key_value:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Invalid authorization format",
                "message": "API key must start with 'llm-router-'",
                "received": auth_header[:50] if auth_header else "None",
                "expected_format": "llm-router-abc123...",
            },
        )

    # Verify the API key
    try:
        redis_client = get_redis()
        key_manager = APIKeyManager(db, redis_client)

        api_key_record = key_manager.verify_api_key(api_key_value)

        if not api_key_record:
            raise HTTPException(status_code=401, detail="Invalid or expired API key")

        if not api_key_record.is_active:
            raise HTTPException(status_code=401, detail="API key is disabled")

        # Update usage count
        key_manager.increment_usage(api_key_record)

        print(f"✅ API key verified: {api_key_record.name}")
        return api_key_record

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ API key verification failed: {e}")
        raise HTTPException(
            status_code=401, detail=f"API key verification failed: {str(e)}"
        )


def get_current_api_key(api_key: APIKey = Depends(verify_api_key)) -> APIKey:
    """Get the current authenticated API key."""
    return api_key
