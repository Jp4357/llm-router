import logging
from typing import Dict, List, Optional, Tuple, Any
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class ClientManager:
    """Manages LLM provider clients."""

    def __init__(self):
        self.clients: Dict[str, Any] = {}
        self.model_to_provider: Dict[str, str] = {}
        self.provider_models: Dict[str, List[str]] = {}
        self.setup_clients()

    def setup_clients(self):
        """Setup clients for all configured providers."""
        from ..config import settings

        try:
            from openai import AsyncOpenAI
        except ImportError:
            logger.error("❌ OpenAI library not installed. Run: pip install openai")
            return

        # OpenAI
        if settings.openai_api_key:
            try:
                self.clients["openai"] = AsyncOpenAI(
                    api_key=settings.openai_api_key,
                    timeout=60.0,
                    max_retries=2,
                    # Remove problematic parameters for compatibility
                )
                self.provider_models["openai"] = [
                    "gpt-4",
                    "gpt-4-turbo",
                    "gpt-4o",
                    "gpt-4o-mini",
                    "gpt-3.5-turbo",
                    "gpt-3.5-turbo-16k",
                ]
                logger.info("✅ OpenAI client initialized")
            except Exception as e:
                logger.error(f"❌ OpenAI client failed: {e}")
                # Try minimal initialization
                try:
                    self.clients["openai"] = AsyncOpenAI(
                        api_key=settings.openai_api_key
                    )
                    self.provider_models["openai"] = ["gpt-3.5-turbo", "gpt-4"]
                    logger.info("✅ OpenAI client initialized (minimal)")
                except Exception as e2:
                    logger.error(f"❌ OpenAI minimal client also failed: {e2}")

        # Gemini (via OpenAI-compatible API)
        if settings.gemini_api_key:
            try:
                self.clients["gemini"] = AsyncOpenAI(
                    base_url=settings.gemini_base_url,
                    api_key=settings.gemini_api_key,
                    timeout=60.0,
                    max_retries=2,
                )
                self.provider_models["gemini"] = [
                    "gemini-1.5-pro",
                    "gemini-1.5-flash",
                    "gemini-pro",
                ]
                logger.info("✅ Gemini client initialized")
            except Exception as e:
                logger.error(f"❌ Gemini client failed: {e}")
                # Try minimal initialization
                try:
                    self.clients["gemini"] = AsyncOpenAI(
                        base_url=settings.gemini_base_url,
                        api_key=settings.gemini_api_key,
                    )
                    self.provider_models["gemini"] = ["gemini-pro"]
                    logger.info("✅ Gemini client initialized (minimal)")
                except Exception as e2:
                    logger.error(f"❌ Gemini minimal client also failed: {e2}")

        # Groq
        if settings.groq_api_key:
            try:
                self.clients["groq"] = AsyncOpenAI(
                    base_url=settings.groq_base_url,
                    api_key=settings.groq_api_key,
                    timeout=60.0,
                    max_retries=2,
                )
                self.provider_models["groq"] = [
                    "llama3-8b-8192",
                    "llama3-70b-8192",
                    "mixtral-8x7b-32768",
                    "gemma-7b-it",
                    "llama2-70b-4096",
                ]
                logger.info("✅ Groq client initialized")
            except Exception as e:
                logger.error(f"❌ Groq client failed: {e}")
                # Try minimal initialization
                try:
                    self.clients["groq"] = AsyncOpenAI(
                        base_url=settings.groq_base_url, api_key=settings.groq_api_key
                    )
                    self.provider_models["groq"] = ["llama3-8b-8192"]
                    logger.info("✅ Groq client initialized (minimal)")
                except Exception as e2:
                    logger.error(f"❌ Groq minimal client also failed: {e2}")

        # Create model-to-provider mapping
        for provider, models in self.provider_models.items():
            for model in models:
                self.model_to_provider[model] = provider

        total_models = len(self.model_to_provider)
        total_providers = len(self.clients)

        if total_providers > 0:
            logger.info(
                f"🚀 Initialized {total_providers} providers with {total_models} models"
            )
        else:
            logger.warning("⚠️ No providers initialized. Check your API keys in .env")

    def get_client_for_model(
        self, model: str, preferred_provider: Optional[str] = None
    ) -> Tuple[Any, str]:
        """Get the appropriate client for a model."""

        # If preferred provider is specified
        if preferred_provider:
            if preferred_provider in self.clients:
                if model in self.provider_models.get(preferred_provider, []):
                    return self.clients[preferred_provider], preferred_provider
                else:
                    available = self.provider_models.get(preferred_provider, [])
                    raise HTTPException(
                        status_code=400,
                        detail=f"Model '{model}' not available for provider '{preferred_provider}'. Available: {available}",
                    )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Provider '{preferred_provider}' not configured or available",
                )

        # Auto-detect provider from model
        provider = self.model_to_provider.get(model)
        if provider and provider in self.clients:
            return self.clients[provider], provider

        # Model not found
        available_models = list(self.model_to_provider.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Model '{model}' not available. Available models: {available_models}",
        )

    def get_available_models(self) -> Dict[str, List[str]]:
        """Get all available models grouped by provider."""
        return {
            provider: models
            for provider, models in self.provider_models.items()
            if provider in self.clients
        }

    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status information for all providers."""
        status = {}

        for provider, client in self.clients.items():
            models = self.provider_models.get(provider, [])
            base_url = "https://api.openai.com/v1"

            if hasattr(client, "_base_url"):
                base_url = str(client._base_url)
            elif provider == "groq":
                base_url = "https://api.groq.com/openai/v1"
            elif provider == "gemini":
                base_url = "https://generativelanguage.googleapis.com/v1"

            status[provider] = {
                "enabled": True,
                "models": models,
                "model_count": len(models),
                "base_url": base_url,
            }

        return status

    def is_provider_available(self, provider: str) -> bool:
        """Check if a provider is available."""
        return provider in self.clients

    def get_model_provider(self, model: str) -> Optional[str]:
        """Get the provider for a specific model."""
        return self.model_to_provider.get(model)


# Global client manager instance
try:
    client_manager = ClientManager()
except Exception as e:
    logger.error(f"❌ Failed to initialize ClientManager: {e}")

    # # Create dummy manager to prevent import errors
    # class DummyClientManager:
    #     def __init__(self):
    #         self.clients = {}
    #         self.model_to_provider = {}
    #         self.provider_models = {}

    #     def get_client_for_model(self, model, preferred_provider=None):
    #         raise HTTPException(status_code=503, detail="No LLM providers available")

    #     def get_available_models(self):
    #         return {}

    #     def get_provider_status(self):
    #         return {}

    #     def is_provider_available(self, provider):
    #         return False

    #     def get_model_provider(self, model):
    #         return None

    # client_manager = DummyClientManager()
