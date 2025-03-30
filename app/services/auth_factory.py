"""
OAuth service factory for different providers.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple

from app.services.auth import (
    create_or_update_user,
    get_google_token,
    get_google_user_info,
)

logger = logging.getLogger(__name__)


class OAuthService(ABC):
    """Abstract base class for OAuth services."""

    @abstractmethod
    async def exchange_code_for_token(
        self, code: str, platform: str = "web", code_verifier: str = None
    ) -> Dict[str, Any]:
        """Exchange authorization code for provider token."""
        pass

    @abstractmethod
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from the provider."""
        pass

    @abstractmethod
    async def authenticate_user(
        self, db, code: str, platform: str = "web", code_verifier: str = None
    ) -> Tuple[Dict[str, Any], bool]:
        """Authenticate a user with the provider, returning user data and whether they're new."""
        pass


class GoogleOAuthService(OAuthService):
    """Google OAuth service implementation."""

    async def exchange_code_for_token(
        self, code: str, platform: str = "web", code_verifier: str = None
    ) -> Dict[str, Any]:
        """Exchange Google authorization code for token."""
        return await get_google_token(code, code_verifier)

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Google."""
        return await get_google_user_info(access_token)

    async def authenticate_user(
        self, db, code: str, platform: str = "web", code_verifier: str = None
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Authenticate a user with Google.

        Args:
            db: Database connection
            code: Authorization code from Google
            platform: Platform identifier (web, ios, android)
            code_verifier: PKCE code verifier (if using PKCE flow)

        Returns:
            Tuple of (user_data, is_new_user)
        """
        # Exchange code for token
        token_data = await self.exchange_code_for_token(code, platform, code_verifier)
        access_token = token_data["access_token"]

        # Get user info
        user_info = await self.get_user_info(access_token)

        # Update user_info with provider metadata
        user_info["provider"] = "google"
        user_info["platform"] = platform

        # Create or update user
        return await create_or_update_user(db, user_info)


class FacebookOAuthService(OAuthService):
    """Facebook OAuth service implementation (placeholder)."""

    async def exchange_code_for_token(
        self, code: str, platform: str = "web", code_verifier: str = None
    ) -> Dict[str, Any]:
        """Exchange Facebook authorization code for token."""
        # TODO: Implement Facebook token exchange
        raise NotImplementedError("Facebook OAuth not implemented yet")

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Facebook."""
        # TODO: Implement Facebook user info retrieval
        raise NotImplementedError("Facebook OAuth not implemented yet")

    async def authenticate_user(
        self, db, code: str, platform: str = "web", code_verifier: str = None
    ) -> Tuple[Dict[str, Any], bool]:
        """Authenticate a user with Facebook."""
        # TODO: Implement Facebook authentication
        raise NotImplementedError("Facebook OAuth not implemented yet")


class OAuthServiceFactory:
    """Factory to create OAuth services based on provider."""

    @staticmethod
    def get_service(provider: str) -> OAuthService:
        """
        Get the appropriate OAuth service for the provider.

        Args:
            provider: The OAuth provider (e.g., "google", "facebook")

        Returns:
            OAuthService implementation for the provider

        Raises:
            ValueError: If the provider is not supported
        """
        if provider == "google":
            return GoogleOAuthService()
        elif provider == "facebook":
            return FacebookOAuthService()
        # Add more providers as needed
        else:
            raise ValueError(f"Unsupported provider: {provider}")
