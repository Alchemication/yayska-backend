from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class OAuthProviderEnum(str, Enum):
    """Enum of supported OAuth providers."""

    GOOGLE = "google"
    FACEBOOK = "facebook"
    # Add more as needed


class OAuthInput(BaseModel):
    """Generic schema for OAuth input."""

    provider: OAuthProviderEnum
    code: str
    platform: str = "web"  # default to web, could be ios, android, etc.
    code_verifier: Optional[str] = None  # PKCE code verifier


class GoogleAuthInput(BaseModel):
    """Schema for input from frontend with Google auth code."""

    code: str = Field(..., description="The authorization code from Google")
    code_verifier: Optional[str] = Field(None, description="PKCE code verifier")


class UserResponse(BaseModel):
    """Schema for the user data in the authentication response."""

    id: int = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email")
    name: str = Field(..., description="User's full name (first_name + last_name)")
    picture: Optional[str] = Field(None, description="URL to user's profile picture")


class AuthResponse(BaseModel):
    """Schema for the authentication response."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    user: UserResponse = Field(..., description="User information")
    is_new_user: bool = Field(..., description="Whether this is a new user")
