import time
import uuid
import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.api_key import APIKey
from ..models.usage_log import UsageLog
from ..schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatCompletionUsage,
    ChatMessage,
)
from ..providers.clients import client_manager
from .dependencies import get_current_api_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/chat", tags=["Chat Completion"])


@router.post("/completions")
async def create_chat_completion(
    request: ChatCompletionRequest,
    current_key: APIKey = Depends(get_current_api_key),
    db: Session = Depends(get_db),
):
    """Create a chat completion using the specified model."""

    try:
        # Get the appropriate client
        client, provider = client_manager.get_client_for_model(
            request.model, request.provider
        )

        # Prepare the OpenAI API request
        openai_request = {
            "model": request.model,
            "messages": [
                {"role": msg.role, "content": msg.content} for msg in request.messages
            ],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": request.stream,
        }

        # Add optional parameters
        if request.top_p is not None:
            openai_request["top_p"] = request.top_p

        logger.info(f"Making request to {provider} with model {request.model}")

        if request.stream:
            # Handle streaming response
            return StreamingResponse(
                stream_chat_completion(
                    client, openai_request, provider, current_key.id, db
                ),
                media_type="text/plain",
            )
        else:
            # Handle regular response
            response = await client.chat.completions.create(**openai_request)

            # Log usage
            await log_usage(
                api_key_id=current_key.id,
                provider=provider,
                model=request.model,
                usage=response.usage,
                db=db,
            )

            # Convert to our response format
            return ChatCompletionResponse(
                id=response.id,
                created=response.created,
                model=response.model,
                provider=provider,
                choices=[
                    ChatCompletionChoice(
                        index=choice.index,
                        message=ChatMessage(
                            role=choice.message.role, content=choice.message.content
                        ),
                        finish_reason=choice.finish_reason,
                    )
                    for choice in response.choices
                ],
                usage=ChatCompletionUsage(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                ),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat completion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat completion failed: {str(e)}")


async def stream_chat_completion(client, request_data, provider, api_key_id, db):
    """Stream chat completion responses."""
    try:
        stream = await client.chat.completions.create(**request_data)

        total_tokens = 0

        async for chunk in stream:
            if chunk.choices:
                # Send the chunk to client
                chunk_data = {
                    "id": chunk.id,
                    "object": "chat.completion.chunk",
                    "created": chunk.created,
                    "model": chunk.model,
                    "provider": provider,
                    "choices": [
                        {
                            "index": choice.index,
                            "delta": {
                                "role": getattr(choice.delta, "role", None),
                                "content": getattr(choice.delta, "content", None),
                            },
                            "finish_reason": choice.finish_reason,
                        }
                        for choice in chunk.choices
                    ],
                }

                yield f"data: {json.dumps(chunk_data)}\n\n"

                # Track token usage (approximate for streaming)
                if hasattr(chunk, "usage") and chunk.usage:
                    total_tokens = chunk.usage.total_tokens

        # Send final message
        yield "data: [DONE]\n\n"

        # Log usage for streaming
        if total_tokens > 0:
            await log_usage(
                api_key_id=api_key_id,
                provider=provider,
                model=request_data["model"],
                usage={
                    "total_tokens": total_tokens,
                    "prompt_tokens": 0,
                    "completion_tokens": total_tokens,
                },
                db=db,
            )

    except Exception as e:
        logger.error(f"Streaming failed: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


async def log_usage(api_key_id: str, provider: str, model: str, usage, db: Session):
    """Log API usage to database."""
    try:
        usage_log = UsageLog(
            id=f"log_{uuid.uuid4().hex[:16]}",
            api_key_id=api_key_id,
            provider=provider,
            model=model,
            endpoint="/v1/chat/completions",
            tokens_used=(
                usage.total_tokens
                if hasattr(usage, "total_tokens")
                else usage.get("total_tokens", 0)
            ),
            prompt_tokens=(
                usage.prompt_tokens
                if hasattr(usage, "prompt_tokens")
                else usage.get("prompt_tokens", 0)
            ),
            completion_tokens=(
                usage.completion_tokens
                if hasattr(usage, "completion_tokens")
                else usage.get("completion_tokens", 0)
            ),
            cost=calculate_cost(provider, model, usage),
        )

        db.add(usage_log)
        db.commit()

    except Exception as e:
        logger.error(f"Failed to log usage: {e}")


def calculate_cost(provider: str, model: str, usage) -> float:
    """Calculate approximate cost based on usage."""
    # Simple cost calculation - you can make this more sophisticated
    total_tokens = (
        usage.total_tokens
        if hasattr(usage, "total_tokens")
        else usage.get("total_tokens", 0)
    )

    # Basic pricing per 1K tokens (these are approximate)
    pricing = {
        "openai": {
            "gpt-4": 0.03,
            "gpt-4-turbo": 0.01,
            "gpt-4o": 0.005,
            "gpt-4o-mini": 0.0015,
            "gpt-3.5-turbo": 0.0015,
        },
        "groq": {"default": 0.0001},
        "gemini": {"default": 0.001},
    }

    provider_pricing = pricing.get(provider, {})
    cost_per_1k = provider_pricing.get(model, provider_pricing.get("default", 0.001))

    return (total_tokens / 1000) * cost_per_1k
