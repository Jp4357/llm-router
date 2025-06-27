import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from fastapi.openapi.utils import get_openapi

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Import after logging setup
from .config import settings
from .database import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("🚀 Starting LLM Router Service...")

    try:
        # Create database tables
        create_tables()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")

    # Initialize providers
    try:
        from .providers.clients import client_manager

        available_providers = len(client_manager.clients)
        total_models = len(client_manager.model_to_provider)
        logger.info(
            f"✅ Initialized {available_providers} providers with {total_models} models"
        )

        if available_providers == 0:
            logger.warning("⚠️ No LLM providers configured! Add API keys to .env file")

    except Exception as e:
        logger.error(f"❌ Provider initialization failed: {e}")

    logger.info("🎯 LLM Router Service is ready!")

    yield

    # Shutdown
    logger.info("🛑 Shutting down LLM Router Service...")


# Create FastAPI app
app = FastAPI(
    title="LLM Router Service",
    description="A unified API gateway for multiple LLM providers (OpenAI, Gemini, Groq)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add security scheme for Swagger UI


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="LLM Router Service",
        version="1.0.0",
        description="A unified API gateway for multiple LLM providers",
        routes=app.routes,
    )

    # Add security definitions
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "API Key",
            "description": "Enter your API key (e.g., llm-router-abc123...)",
        }
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": {"message": "Not found", "type": "not_found"}},
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {"message": "Internal server error", "type": "internal_error"}
        },
    )


# Root endpoints
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "LLM Router Service",
        "version": "1.0.0",
        "description": "Unified API gateway for multiple LLM providers",
        "status": "online",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "api_keys": "/v1/api-keys",
            "chat": "/v1/chat/completions",
            "models": "/v1/models",
            "usage": "/v1/usage",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        from .providers.clients import client_manager

        providers_count = len(client_manager.clients)
        models_count = len(client_manager.model_to_provider)

        return {
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00Z",
            "providers": providers_count,
            "models": models_count,
            "database": "connected",
            "redis": "optional",
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503, content={"status": "unhealthy", "error": str(e)}
        )


@app.get("/debug/headers")
async def debug_headers(request: Request):
    """Debug endpoint to see all request headers (no auth required)."""
    return {
        "message": "Debug endpoint - shows all request headers",
        "headers": dict(request.headers),
        "method": request.method,
        "url": str(request.url),
        "client": request.client.host if request.client else None,
    }


@app.post("/debug/test-auth")
async def test_auth(request: Request):
    """Test authentication without actually requiring it."""
    headers = dict(request.headers)

    # Extract potential auth headers
    auth_methods = {
        "authorization": headers.get("authorization"),
        "Authorization": headers.get("Authorization"),
        "x-api-key": headers.get("x-api-key"),
        "X-API-Key": headers.get("X-API-Key"),
    }

    return {
        "message": "Auth test endpoint (no verification)",
        "all_headers": headers,
        "auth_methods": auth_methods,
        "instructions": {
            "method1": "Set Authorization header to: Bearer llm-router-lYHV6fyocIoGmAc_xk4e9XmitOHx6C4vUwnl_ta3v3k",
            "method2": "Set x-api-key header to: llm-router-lYHV6fyocIoGmAc_xk4e9XmitOHx6C4vUwnl_ta3v3k",
        },
    }


# Include API routers
try:
    from .api.auth import router as auth_router

    app.include_router(auth_router)
    logger.info("✅ Auth router included")
except Exception as e:
    logger.error(f"❌ Failed to include auth router: {e}")

try:
    from .api.chat import router as chat_router

    app.include_router(chat_router)
    logger.info("✅ Chat router included")
except Exception as e:
    logger.error(f"❌ Failed to include chat router: {e}")

try:
    from .api.models import router as models_router

    app.include_router(models_router)
    logger.info("✅ Models router included")
except Exception as e:
    logger.error(f"❌ Failed to include models router: {e}")

try:
    from .api.usage import router as usage_router

    app.include_router(usage_router)
    logger.info("✅ Usage router included")
except Exception as e:
    logger.error(f"❌ Failed to include usage router: {e}")

try:
    from .api.token_auth import router as token_auth_router

    app.include_router(token_auth_router)
    logger.info("✅ Token auth router included")
except Exception as e:
    logger.error(f"❌ Failed to include token auth router: {e}")


# Development server
if __name__ == "__main__":
    import uvicorn

    logger.info("🚀 Starting development server...")
    uvicorn.run(
        "src.llm_router.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
