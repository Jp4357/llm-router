# =============================================================================
# src/llm_router/api/models.py - Models API Routes
# =============================================================================
"""API routes for listing available models and providers."""

from fastapi import APIRouter, Depends, HTTPException

from ..models.api_key import APIKey
from ..schemas import ModelsResponse, ModelInfo, ProvidersResponse, ProviderInfo
from ..providers.clients import client_manager
from .dependencies import get_current_api_key

router = APIRouter(prefix="/v1/models", tags=["Models"])


@router.get("/", response_model=ModelsResponse)
async def list_models(current_key: APIKey = Depends(get_current_api_key)):
    """List all available models across all providers."""
    try:
        available_models = client_manager.get_available_models()

        models_list = []
        for provider, model_list in available_models.items():
            for model in model_list:
                models_list.append(
                    ModelInfo(id=model, provider=provider, owned_by=provider)
                )

        return ModelsResponse(data=models_list)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list models: {str(e)}")


@router.get("/providers", response_model=ProvidersResponse)
async def list_providers(current_key: APIKey = Depends(get_current_api_key)):
    """List all available providers and their status."""
    try:
        provider_status = client_manager.get_provider_status()

        providers_data = {}
        for provider, status in provider_status.items():
            providers_data[provider] = ProviderInfo(
                name=provider,
                enabled=status["enabled"],
                models=status["models"],
                model_count=status["model_count"],
                base_url=status["base_url"],
            )

        return ProvidersResponse(data=providers_data)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list providers: {str(e)}"
        )


@router.get("/{model_id}")
async def get_model_info(
    model_id: str, current_key: APIKey = Depends(get_current_api_key)
):
    """Get information about a specific model."""
    try:
        provider = client_manager.get_model_provider(model_id)

        if not provider:
            available_models = list(client_manager.model_to_provider.keys())
            raise HTTPException(
                status_code=404,
                detail=f"Model '{model_id}' not found. Available models: {available_models}",
            )

        return ModelInfo(id=model_id, provider=provider, owned_by=provider)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get model info: {str(e)}"
        )
