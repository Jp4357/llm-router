from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db, get_redis
from ..models.api_key import APIKey
from ..schemas import APIKeyRequest, APIKeyResponse, APIKeyInfo
from ..utils.auth import APIKeyManager
from .dependencies import get_current_api_key

router = APIRouter(prefix="/v1/api-keys", tags=["Authentication"])


@router.post("/", response_model=APIKeyResponse)
async def create_api_key(request: APIKeyRequest, db: Session = Depends(get_db)):
    """Create a new API key."""
    try:
        redis_client = get_redis()
        key_manager = APIKeyManager(db, redis_client)

        api_key = key_manager.create_api_key(request)

        return api_key

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create API key: {str(e)}"
        )


@router.get("/", response_model=List[APIKeyInfo])
async def list_api_keys(
    current_key: APIKey = Depends(get_current_api_key), db: Session = Depends(get_db)
):
    """List API keys (returns only the current key for security)."""
    try:
        # For security, only return the current API key's info
        return [
            APIKeyInfo(
                id=current_key.id,
                name=current_key.name,
                description=current_key.description,
                created_at=current_key.created_at,
                rate_limit=current_key.rate_limit,
                usage_count=current_key.usage_count,
            )
        ]

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list API keys: {str(e)}"
        )


@router.get("/current", response_model=APIKeyInfo)
async def get_current_key_info(current_key: APIKey = Depends(get_current_api_key)):
    """Get information about the current API key."""
    return APIKeyInfo(
        id=current_key.id,
        name=current_key.name,
        description=current_key.description,
        created_at=current_key.created_at,
        rate_limit=current_key.rate_limit,
        usage_count=current_key.usage_count,
    )


@router.delete("/{key_id}")
async def delete_api_key(
    key_id: str,
    current_key: APIKey = Depends(get_current_api_key),
    db: Session = Depends(get_db),
):
    """Delete an API key (can only delete your own key)."""
    try:
        if key_id != current_key.id:
            raise HTTPException(
                status_code=403, detail="You can only delete your own API key"
            )

        # Soft delete - just mark as inactive
        current_key.is_active = False
        db.commit()

        return {"message": "API key deactivated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete API key: {str(e)}"
        )
