import os
from contextlib import asynccontextmanager
from typing import Any, Dict

import structlog
from dotenv import load_dotenv

# Load .env file before importing app modules
load_dotenv(override=True)

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import (
    IntegrityError,
    OperationalError,
    SQLAlchemyError,
)

from app.api.v1.router import api_router
from app.config import settings
from app.exceptions import YayskaException
from app.middleware.auth import setup_auth_middleware

logger = structlog.get_logger()


# Define allowed origins
CORS_ORIGINS = (
    ["http://localhost:8081"]
    if os.getenv("ENVIRONMENT") == "local"
    else [
        "https://yayska-frontend.vercel.app",
        "https://yayska.ie",
        "https://yayska.com",
    ]
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application."""
    logger.info("Starting up FastAPI application")
    # Initialize cache before yielding (remove in serverless)
    # FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache")
    try:
        yield
    finally:
        # Clean up if needed
        logger.info("Shutting down FastAPI application")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)


# Add this function after creating the FastAPI app
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=app.title,
        version="1.0.0",
        description="Yayska Backend API - Educational platform for Irish primary school children",
        routes=app.routes,
    )

    # Add Bearer token security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter JWT token (without 'Bearer ' prefix)",
        }
    }

    # Auth endpoints that don't require authentication
    public_auth_endpoints = {"/oauth/callback", "/google/callback", "/refresh"}

    # Apply security to protected endpoints
    for path, path_data in openapi_schema["paths"].items():
        for method, method_data in path_data.items():
            if method.upper() != "OPTIONS":
                # Skip health checks and public auth endpoints
                tags = method_data.get("tags", [])
                is_health_endpoint = any(tag in ["health"] for tag in tags)
                is_public_auth_endpoint = any(
                    path.endswith(endpoint) for endpoint in public_auth_endpoints
                )

                if not is_health_endpoint and not is_public_auth_endpoint:
                    method_data["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Exception handlers
@app.exception_handler(YayskaException)
async def yayska_exception_handler(
    request: Request, exc: YayskaException
) -> JSONResponse:
    """Handle custom Yayska application exceptions."""
    logger.error(
        "Yayska application error",
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
        path=request.url.path,
        method=request.method,
    )

    response_content: Dict[str, Any] = {
        "error": {
            "code": exc.error_code,
            "message": exc.message,
        }
    }

    # Add details if available and not in production
    if exc.details and os.getenv("ENVIRONMENT") != "production":
        response_content["error"]["details"] = exc.details

    return JSONResponse(status_code=exc.status_code, content=response_content)


@app.exception_handler(PydanticValidationError)
async def pydantic_validation_exception_handler(
    request: Request, exc: PydanticValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    logger.error(
        "Validation error",
        errors=exc.errors(),
        path=request.url.path,
        method=request.method,
    )

    # Format validation errors in a user-friendly way
    formatted_errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        formatted_errors.append(
            {
                "field": field_path,
                "message": error["msg"],
                "type": error["type"],
            }
        )

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Input validation failed",
                "details": {"validation_errors": formatted_errors},
            }
        },
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(
    request: Request, exc: IntegrityError
) -> JSONResponse:
    """Handle database integrity errors (unique constraints, foreign keys, etc.)."""
    logger.error(
        "Database integrity error",
        error=str(exc.orig) if exc.orig else str(exc),
        path=request.url.path,
        method=request.method,
    )

    # Try to provide more specific error messages
    error_msg = str(exc.orig) if exc.orig else str(exc)

    if "unique constraint" in error_msg.lower():
        message = "A record with this information already exists"
    elif "foreign key constraint" in error_msg.lower():
        message = "Referenced record does not exist"
    elif "not null constraint" in error_msg.lower():
        message = "Required field is missing"
    else:
        message = "Data integrity error"

    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "INTEGRITY_ERROR",
                "message": message,
            }
        },
    )


@app.exception_handler(OperationalError)
async def operational_error_handler(
    request: Request, exc: OperationalError
) -> JSONResponse:
    """Handle database operational errors (connection issues, etc.)."""
    logger.error(
        "Database operational error",
        error=str(exc.orig) if exc.orig else str(exc),
        path=request.url.path,
        method=request.method,
    )

    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": "DATABASE_UNAVAILABLE",
                "message": "Database is temporarily unavailable. Please try again later.",
            }
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """Handle other SQLAlchemy database errors with better error extraction."""
    from app.exceptions import extract_sql_error_message

    # Extract meaningful error message
    user_message, technical_details = extract_sql_error_message(exc)

    logger.exception(
        "Database error",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        method=request.method,
        technical_details=technical_details,
    )

    response_content = {
        "error": {
            "code": "DATABASE_ERROR",
            "message": user_message,
        }
    }

    # In development, add full technical details
    if os.getenv("ENVIRONMENT") == "local":
        response_content["error"]["details"] = {
            "technical_details": technical_details,
            "exception_type": type(exc).__name__,
        }

    return JSONResponse(
        status_code=500,
        content=response_content,
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTPExceptions."""
    logger.error(
        "HTTP error",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail,
            }
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for all unhandled exceptions."""
    logger.exception(
        "Unhandled exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        method=request.method,
    )

    # In development, include more details
    response_content = {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred. Please try again later.",
        }
    }

    # if os.getenv("ENVIRONMENT") == "local":
    #     response_content["error"]["details"] = {
    #         "exception_type": type(exc).__name__,
    #         "exception_message": str(exc),
    #         "traceback": str(exc.__traceback__) if exc.__traceback__ else None,
    #     }
    #     # Also add the full error as the message in local development
    #     response_content["error"]["message"] = f"{type(exc).__name__}: {str(exc)}"

    return JSONResponse(status_code=500, content=response_content)


# Set CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup auth middleware (must be after CORS middleware)
setup_auth_middleware(app)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Export the app object
app = app
