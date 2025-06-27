"""Usage statistics API routes for tracking API consumption."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..api.dependencies import verify_api_key
from ..models import APIKey, UsageLog
from ..schemas import UsageResponse

router = APIRouter(prefix="/v1/usage", tags=["Usage"])


@router.get("/", response_model=UsageResponse)
async def get_usage(
    api_key: APIKey = Depends(verify_api_key), db: Session = Depends(get_db)
):
    """Get usage statistics for the authenticated API key."""
    try:
        # Get usage logs for this API key
        logs = db.query(UsageLog).filter(UsageLog.api_key_id == api_key.id).all()

        total_requests = len(logs)
        total_tokens = sum(log.tokens_used or 0 for log in logs)
        total_cost = sum(log.cost or 0.0 for log in logs)

        # Provider breakdown
        provider_stats = (
            db.query(
                UsageLog.provider,
                func.count(UsageLog.id).label("requests"),
                func.sum(UsageLog.tokens_used).label("tokens"),
                func.sum(UsageLog.cost).label("cost"),
            )
            .filter(UsageLog.api_key_id == api_key.id)
            .group_by(UsageLog.provider)
            .all()
        )

        provider_breakdown = {}
        for stat in provider_stats:
            provider_breakdown[stat.provider] = {
                "requests": stat.requests,
                "tokens": stat.tokens or 0,
                "cost": float(stat.cost or 0.0),
            }

        return UsageResponse(
            api_key_id=api_key.id,
            total_requests=total_requests,
            total_tokens=total_tokens,
            total_cost=total_cost,
            provider_breakdown=provider_breakdown,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get usage stats: {str(e)}"
        )


@router.get("/summary")
async def get_usage_summary(api_key: APIKey = Depends(verify_api_key)):
    """Get a quick usage summary."""
    return {
        "api_key_id": api_key.id,
        "message": "Usage tracking is active",
        "rate_limit": api_key.rate_limit,
        "current_usage": api_key.usage_count,
    }
