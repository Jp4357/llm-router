from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime


# =============================================================================
# Chat Completion Schemas
# =============================================================================


class ChatMessage(BaseModel):
    """Single chat message."""

    role: str = Field(..., description="Role: system, user, or assistant")
    content: str = Field(..., description="Message content")


class ChatCompletionRequest(BaseModel):
    """Chat completion request."""

    model: str = Field(..., description="Model to use")
    messages: List[ChatMessage] = Field(..., description="List of messages")
    max_tokens: Optional[int] = Field(150, description="Maximum tokens to generate")
    temperature: Optional[float] = Field(0.7, description="Sampling temperature")
    top_p: Optional[float] = Field(1.0, description="Top-p sampling")
    stream: Optional[bool] = Field(False, description="Stream response")
    provider: Optional[str] = Field(None, description="Force specific provider")


class ChatCompletionChoice(BaseModel):
    """Single completion choice."""

    index: int
    message: ChatMessage
    finish_reason: str


class ChatCompletionUsage(BaseModel):
    """Token usage information."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """Chat completion response."""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    provider: str
    choices: List[ChatCompletionChoice]
    usage: ChatCompletionUsage


# =============================================================================
# API Key Schemas
# =============================================================================


class APIKeyRequest(BaseModel):
    """Request to create new API key."""

    name: str = Field(..., description="Friendly name for the API key")
    description: Optional[str] = Field("", description="Optional description")


class APIKeyResponse(BaseModel):
    """API key creation response."""

    id: str
    name: str
    key: str
    description: str
    created_at: datetime
    rate_limit: int
    usage_count: int


class APIKeyInfo(BaseModel):
    """API key information (without the actual key)."""

    id: str
    name: str
    description: str
    created_at: datetime
    rate_limit: int
    usage_count: int


# =============================================================================
# Model Schemas
# =============================================================================


class ModelInfo(BaseModel):
    """Information about an available model."""

    id: str
    object: str = "model"
    provider: str
    owned_by: str


class ModelsResponse(BaseModel):
    """Response containing available models."""

    object: str = "list"
    data: List[ModelInfo]


class ProviderInfo(BaseModel):
    """Information about a provider."""

    model_config = {"protected_namespaces": ()}

    name: str
    enabled: bool
    models: List[str]
    model_count: int
    base_url: str


class ProvidersResponse(BaseModel):
    """Response containing provider information."""

    object: str = "list"
    data: Dict[str, ProviderInfo]


# =============================================================================
# Usage Schemas
# =============================================================================


class ProviderUsage(BaseModel):
    """Usage statistics for a specific provider."""

    requests: int
    tokens: int
    cost: float


class UsageResponse(BaseModel):
    """Usage statistics response."""

    api_key_id: str
    total_requests: int
    total_tokens: int
    total_cost: float
    provider_breakdown: Dict[str, ProviderUsage]


# =============================================================================
# Error Schemas
# =============================================================================


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: Dict[str, Any]


class ErrorDetail(BaseModel):
    """Error detail."""

    message: str
    type: str
    code: Optional[str] = None
