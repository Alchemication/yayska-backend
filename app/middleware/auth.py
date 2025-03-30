import logging
from typing import Callable, List, Optional

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce authentication for all routes except those explicitly excluded.
    """

    def __init__(
        self,
        app: ASGIApp,
        public_paths: Optional[List[str]] = None,
        public_path_prefixes: Optional[List[str]] = None,
    ):
        """
        Initialize the auth middleware.

        Args:
            app: The ASGI app
            public_paths: List of exact paths that are publicly accessible
            public_path_prefixes: List of path prefixes that are publicly accessible
        """
        super().__init__(app)
        # Default public paths
        self.public_paths = public_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/openapi.json",
            "/api/v1/auth/google/callback",
            "/api/v1/auth/oauth/callback",  # Generic OAuth endpoint
            "/api/v1/auth/refresh",  # Token refresh endpoint
            "/api/v1/health",
        ]

        # Default public path prefixes
        self.public_path_prefixes = public_path_prefixes or [
            "/docs/",
            "/redoc/",
            "/static/",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process each request and determine if authentication is required.

        Args:
            request: The incoming request
            call_next: The next middleware or endpoint handler

        Returns:
            The response
        """
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Check if the path is in public paths or starts with a public prefix
        path = request.url.path

        # Allow public paths without authentication
        if path in self.public_paths:
            return await call_next(request)

        # Allow paths with public prefixes
        for prefix in self.public_path_prefixes:
            if path.startswith(prefix):
                return await call_next(request)

        # For all other paths, check for Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Authentication required"},
            )

        # If we got here, the request has a Bearer token
        # The actual token validation will happen in the endpoint's dependency
        return await call_next(request)


def setup_auth_middleware(app: FastAPI):
    """
    Set up the authentication middleware for the application.

    Args:
        app: The FastAPI application
    """
    app.add_middleware(AuthMiddleware)
