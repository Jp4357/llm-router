from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from datetime import timedelta

from ..database import get_db
from ..models.api_key import APIKey
from ..utils.auth import APIKeyManager
from ..utils.tokens import TokenManager

router = APIRouter(prefix="/auth", tags=["Token Authentication"])


class TokenRequest(BaseModel):
    """Request to create a new token."""

    api_key: str = Field(..., description="Your API key")
    expires_in_hours: Optional[int] = Field(
        24, description="Token expiry in hours", ge=1, le=168
    )  # Max 7 days


class TokenResponse(BaseModel):
    """Token creation response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    expires_at: str
    api_key_id: str
    api_key_name: str


class RefreshTokenRequest(BaseModel):
    """Request to refresh a token."""

    token: str = Field(..., description="Current token to refresh")


@router.post("/token", response_model=TokenResponse)
async def create_token(request: TokenRequest, db: Session = Depends(get_db)):
    """
    Create a JWT token using your API key.

    This endpoint allows you to exchange your API key for a temporary JWT token
    that can be used to authenticate API requests.
    """
    try:
        # Verify the API key
        key_manager = APIKeyManager(db, None)
        api_key_record = key_manager.verify_api_key(request.api_key)

        if not api_key_record:
            raise HTTPException(status_code=401, detail="Invalid API key")

        if not api_key_record.is_active:
            raise HTTPException(status_code=401, detail="API key is disabled")

        # Create JWT token
        token_manager = TokenManager(db)
        expires_in = timedelta(hours=request.expires_in_hours)

        token_data = token_manager.create_token(
            api_key_id=api_key_record.id, expires_in=expires_in
        )

        # Update API key usage
        key_manager.increment_usage(api_key_record)

        return TokenResponse(**token_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create token: {str(e)}")


@router.post("/token/form", response_model=TokenResponse)
async def create_token_form(
    api_key: str = Form(..., description="Your API key"),
    expires_in_hours: int = Form(24, description="Token expiry in hours"),
    db: Session = Depends(get_db),
):
    """
    Create a JWT token using form data (alternative to JSON).

    This is useful for testing with curl or form-based tools.
    """
    request = TokenRequest(api_key=api_key, expires_in_hours=expires_in_hours)
    return await create_token(request, db)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Refresh an existing JWT token.

    This creates a new token with a fresh expiry time.
    """
    try:
        token_manager = TokenManager(db)

        new_token_data = token_manager.refresh_token(request.token)

        if not new_token_data:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        return TokenResponse(**new_token_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to refresh token: {str(e)}"
        )


@router.post("/verify")
async def verify_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Verify a JWT token and return its details.

    This endpoint checks if a token is valid and returns information about it.
    """
    try:
        token_manager = TokenManager(db)

        token_data = token_manager.verify_token(request.token)

        if not token_data:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        return {
            "valid": True,
            "api_key_id": token_data["api_key_id"],
            "api_key_name": token_data["api_key_name"],
            "token_id": token_data["token_id"],
            "expires_at": token_data["expires_at"],
            "message": "Token is valid",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to verify token: {str(e)}")


@router.delete("/revoke")
async def revoke_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Revoke a JWT token.

    This marks a token as invalid (though for JWT, it will still be valid until expiry).
    """
    try:
        token_manager = TokenManager(db)

        is_valid = token_manager.revoke_token(request.token)

        if not is_valid:
            raise HTTPException(status_code=401, detail="Invalid token")

        return {
            "message": "Token revoked successfully",
            "note": "JWT tokens cannot be truly revoked until expiry - use short expiry times for security",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to revoke token: {str(e)}")
