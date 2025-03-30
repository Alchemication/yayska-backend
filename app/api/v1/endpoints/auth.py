import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import text

from app.database import get_db
from app.schemas.auth import AuthResponse, GoogleAuthInput, OAuthInput
from app.services.auth import (
    blacklist_token,
    blacklist_user_tokens,
    create_access_token,
    create_refresh_token,
    decode_token,
    security,
)
from app.services.auth_factory import OAuthServiceFactory
from app.utils.deps import CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()


class TokenRefreshRequest(BaseModel):
    """Schema for token refresh request."""

    refresh_token: str


class TokenRefreshResponse(BaseModel):
    """Schema for token refresh response."""

    access_token: str
    refresh_token: str


@router.post("/oauth/callback", response_model=AuthResponse)
async def oauth_callback(data: OAuthInput, db=Depends(get_db)) -> AuthResponse:
    """
    Handle OAuth callback with authorization code for any supported provider.

    Args:
        data: The OAuth authorization data including provider, code, and platform
        db: Database connection

    Returns:
        Auth response with tokens and user info
    """
    try:
        # Get the appropriate OAuth service
        oauth_service = OAuthServiceFactory.get_service(data.provider)

        # Authenticate user with the service
        user, is_new_user = await oauth_service.authenticate_user(
            db, data.code, data.platform, data.code_verifier
        )

        # Create tokens
        access_token = create_access_token(user["id"])
        refresh_token = create_refresh_token(user["id"])

        # Prepare response
        response_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "name": user["name"],
                "picture": user.get("picture_url"),
            },
            "is_new_user": is_new_user,
        }

        return response_data
    except ValueError as e:
        logger.error(f"Invalid OAuth provider: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotImplementedError as e:
        logger.error(f"Unsupported OAuth provider implementation: {str(e)}")
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in OAuth callback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed",
        )


@router.post("/google/callback", response_model=AuthResponse)
async def google_oauth_callback(
    data: GoogleAuthInput, db=Depends(get_db)
) -> AuthResponse:
    """
    Handle Google OAuth callback with authorization code.

    The frontend will send the Google authorization code to this endpoint.
    This endpoint will:
    1. Exchange the code for Google tokens
    2. Get the user's info from Google
    3. Create or update the user in our database
    4. Generate JWT tokens
    5. Return tokens and user info

    Args:
        data: The Google authorization code
        db: Database connection

    Returns:
        Auth response with tokens and user info
    """
    # Convert the Google-specific input to the generic OAuth input
    oauth_input = OAuthInput(
        provider="google",
        code=data.code,
        platform="web",
        code_verifier=data.code_verifier,
    )

    # Use the generic OAuth endpoint
    return await oauth_callback(oauth_input, db)


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(data: TokenRefreshRequest, db=Depends(get_db)):
    """
    Refresh the access token using a refresh token.

    Args:
        data: The refresh token request
        db: Database connection

    Returns:
        New access and refresh tokens
    """
    try:
        # Decode and validate the refresh token
        payload = await decode_token(data.refresh_token, db)

        # Check if token is refresh token
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
            )

        # Check if user exists
        query = """
            SELECT id FROM users
            WHERE id = :user_id AND deleted_at IS NULL
        """
        result = await db.execute(text(query), {"user_id": int(user_id)})
        result = result.mappings().first()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or deleted",
            )

        # Create new tokens
        new_access_token = create_access_token(int(user_id))
        new_refresh_token = create_refresh_token(int(user_id))

        return {"access_token": new_access_token, "refresh_token": new_refresh_token}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in token refresh: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token refresh failed"
        )


@router.get("/me")
async def get_current_user_info(current_user: CurrentUser):
    """
    Get information about the currently authenticated user.
    This endpoint is protected and requires a valid JWT token.

    Args:
        current_user: The authenticated user (injected by dependency)

    Returns:
        The current user information
    """
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "name": current_user["name"],
        "picture": current_user.get("picture_url"),
    }


@router.post("/logout")
async def logout(
    db=Depends(get_db), credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Log out a user by adding their access token to the blacklist.

    This endpoint invalidates the current token, but not any other sessions.
    For that, use the logout_all_sessions endpoint.

    Args:
        db: Database connection
        credentials: HTTP Authorization credentials with Bearer token

    Returns:
        Success message
    """
    try:
        token = credentials.credentials
        payload = await decode_token(token)

        # Check if token is access token
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )

        user_id = int(payload.get("sub", 0))
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
            )

        # Get token expiration time
        expires_at = datetime.fromtimestamp(payload.get("exp", 0), tz=timezone.utc)

        # Add token to blacklist
        await blacklist_token(db, token, user_id, "access", expires_at)

        # Return success message (frontend only needs 200 status)
        return {"status": "success", "message": "Logged out successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in logout: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Logout failed"
        )


@router.post("/logout/all")
async def logout_all_sessions(current_user: CurrentUser, db=Depends(get_db)):
    """
    Log out a user from all sessions by blacklisting all their tokens.

    This is useful for security-sensitive operations like password changes.

    Args:
        db: Database connection
        current_user: The authenticated user (injected by dependency)

    Returns:
        Success message
    """
    try:
        user_id = current_user["id"]

        # Blacklist all tokens for this user
        await blacklist_user_tokens(db, user_id)

        # Return success message (frontend only needs 200 status)
        return {
            "status": "success",
            "message": "Logged out of all sessions successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in logout all sessions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout from all sessions failed",
        )
