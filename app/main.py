from contextlib import asynccontextmanager

import structlog
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.router import api_router
from app.config import settings
from app.database import get_connection_pool

# Load .env file before importing settings
load_dotenv()


logger = structlog.get_logger()


class AppException(Exception):
    """Base exception class for application-specific errors."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


# Define allowed origins
CORS_ORIGINS = ["http://localhost:3000", "https://yayska-frontend.vercel.app"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up FastAPI application")
    if settings.ENVIRONMENT == "local":
        try:
            # Test database connection only in local environment
            pool = await get_connection_pool()
            async with pool.acquire() as conn:
                version = await conn.fetchval("SELECT version();")
                logger.info(f"Connected to PostgreSQL: {version}")
            await pool.close()
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
    yield
    logger.info("Shutting down FastAPI application")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)


# Then add the exception handlers
@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """Handle database-specific errors."""
    error_msg = f"Database error occurred: {str(exc)}"
    logger.exception(
        error_msg,
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        method=request.method,
    )

    return JSONResponse(
        status_code=500,
        content={"detail": "Database operation failed. Please try again later."},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    logger.error(
        "HTTP error occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method,
    )

    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle application-specific exceptions."""
    logger.error(
        "Application error occurred",
        error=exc.message,
        status_code=exc.status_code,
        path=request.url.path,
        method=request.method,
    )

    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for all unhandled exceptions."""
    error_msg = f"Unhandled error occurred: {str(exc)}"
    logger.exception(
        error_msg,
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        method=request.method,
    )

    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )


# Set CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Export the app object
app = app
