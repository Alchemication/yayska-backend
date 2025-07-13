import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Tuple

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text

from app.config import settings

logger = logging.getLogger(__name__)

# Security scheme for JWT Bearer token
security = HTTPBearer()


async def get_google_token(code: str, code_verifier: str = None) -> Dict[str, Any]:
    """
    Exchange authorization code for access token from Google.

    Args:
        code: The authorization code from Google OAuth flow
        code_verifier: The PKCE code verifier used in the authorization request

    Returns:
        Dict containing tokens and user info from Google

    Raises:
        HTTPException: If token exchange fails
    """
    try:
        # Exchange code for token
        async with httpx.AsyncClient() as client:
            token_data = {
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            }

            # Add code_verifier if provided (required for PKCE flow)
            if code_verifier:
                token_data["code_verifier"] = code_verifier

            response = await client.post(
                settings.GOOGLE_TOKEN_URL,
                data=token_data,
            )

            if response.status_code != 200:
                logger.error(f"Google token exchange failed: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Failed to authenticate with Google",
                )

            return response.json()
    except Exception as e:
        logger.error(f"Error exchanging Google code for token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed"
        )


async def get_google_user_info(access_token: str) -> Dict[str, Any]:
    """
    Get user info from Google with the access token.

    Args:
        access_token: Google OAuth access token

    Returns:
        Dict containing user information from Google

    Raises:
        HTTPException: If fetching user info fails
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                settings.GOOGLE_USER_INFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.status_code != 200:
                logger.error(f"Google user info fetch failed: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Failed to get user info from Google",
                )

            return response.json()
    except Exception as e:
        logger.error(f"Error fetching Google user info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Failed to get user info"
        )


async def create_or_update_user(
    db, google_user_info: Dict[str, Any]
) -> Tuple[Dict[str, Any], bool]:
    """
    Create or update a user based on OAuth information.

    Args:
        db: Database connection
        google_user_info: User information from OAuth provider

    Returns:
        Tuple containing (user_dict, is_new_user)

    Raises:
        HTTPException: If database operation fails
    """
    try:
        # Extract provider info
        provider = google_user_info.get(
            "provider", "google"
        )  # Default to google for backward compatibility
        platform = google_user_info.get(
            "platform", "web"
        )  # Default to web for backward compatibility
        provider_user_id = google_user_info["id"]  # OAuth provider's user ID
        email = google_user_info["email"]

        # Check if user exists with this provider user ID
        query = """
            SELECT id, email, first_name, last_name, picture_url, provider, provider_user_id
            FROM users
            WHERE provider = :provider AND provider_user_id = :provider_user_id
        """
        result = await db.execute(
            text(query), {"provider": provider, "provider_user_id": provider_user_id}
        )
        result = result.mappings().first()

        is_new_user = False

        if not result:
            # Check if user exists with this email but no provider ID
            query = """
                SELECT id, email, first_name, last_name, picture_url, provider, provider_user_id
                FROM users
                WHERE email = :email AND provider_user_id IS NULL
            """
            result = await db.execute(text(query), {"email": email})
            result = result.mappings().first()

            if result:
                # Update existing user with provider ID
                query = """
                    UPDATE users
                    SET provider = :provider,
                        provider_user_id = :provider_user_id,
                        platform = :platform,
                        provider_data = :provider_data,
                        picture_url = :picture_url,
                        updated_at = :updated_at
                    WHERE email = :email
                    RETURNING id, email, first_name, last_name, picture_url, memory
                """

                # Convert user info to JSON for provider_data

                provider_data = json.dumps(google_user_info)

                current_time = datetime.now(timezone.utc)

                result = await db.execute(
                    text(query),
                    {
                        "provider": provider,
                        "provider_user_id": provider_user_id,
                        "platform": platform,
                        "provider_data": provider_data,
                        "picture_url": google_user_info.get("picture"),
                        "updated_at": current_time,
                        "email": email,
                    },
                )
                result = result.mappings().first()
            else:
                # Create new user
                first_name = google_user_info.get("given_name", "")
                last_name = google_user_info.get("family_name", "")
                picture_url = google_user_info.get("picture")

                provider_data = json.dumps(google_user_info)
                current_time = datetime.now(timezone.utc)

                query = """
                    INSERT INTO users (
                        email, first_name, last_name, picture_url, 
                        provider, provider_user_id, platform, provider_data,
                        is_verified, created_at, updated_at, last_login_at
                    )
                    VALUES (
                        :email, :first_name, :last_name, :picture_url, 
                        :provider, :provider_user_id, :platform, :provider_data,
                        true, :current_time, :current_time, :current_time
                    )
                    RETURNING id, email, first_name, last_name, picture_url, memory
                """
                result = await db.execute(
                    text(query),
                    {
                        "email": email,
                        "first_name": first_name,
                        "last_name": last_name,
                        "picture_url": picture_url,
                        "provider": provider,
                        "provider_user_id": provider_user_id,
                        "platform": platform,
                        "provider_data": provider_data,
                        "current_time": current_time,
                    },
                )
                result = result.mappings().first()
                is_new_user = True

        # Update last login
        query = """
            UPDATE users
            SET last_login_at = :last_login_at
            WHERE id = :id
        """
        await db.execute(
            text(query),
            {"last_login_at": datetime.now(timezone.utc), "id": result["id"]},
        )

        # Re-fetch the full user object to ensure all fields are present, including memory
        query = """
            SELECT id, email, first_name, last_name, picture_url, memory
            FROM users
            WHERE id = :id
        """
        refreshed_result = await db.execute(text(query), {"id": result["id"]})
        user_row = refreshed_result.mappings().first()

        # Convert to dict and add full name
        user_dict = dict(user_row)
        user_dict["name"] = (
            f"{user_dict['first_name']} {user_dict['last_name']}".strip()
        )

        return user_dict, is_new_user

    except Exception as e:
        logger.error(f"Database error in create_or_update_user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing user data",
        )


def create_access_token(user_id: int) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User ID to encode in the token

    Returns:
        Encoded JWT token string
    """
    expires_delta = timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
    expire = datetime.now(timezone.utc) + expires_delta

    to_encode = {"sub": str(user_id), "exp": expire, "type": "access"}

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """
    Create a JWT refresh token.

    Args:
        user_id: User ID to encode in the token

    Returns:
        Encoded JWT token string
    """
    expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    expire = datetime.now(timezone.utc) + expires_delta

    to_encode = {"sub": str(user_id), "exp": expire, "type": "refresh"}

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


async def decode_token(token: str, db=None) -> Dict[str, Any]:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string
        db: Optional database connection to check blacklist

    Returns:
        Dict containing the decoded token payload

    Raises:
        HTTPException: If token is invalid, expired, or blacklisted
    """
    try:
        # Check if token is blacklisted (if db is provided)
        if db and await is_token_blacklisted(db, token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )

        # Decode the token
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )

        # If database is available, check if user has been logged out of all sessions
        if db and "sub" in payload:
            user_id = int(payload["sub"])
            query = """
                SELECT EXISTS(
                    SELECT 1 FROM token_blacklist 
                    WHERE user_id = :user_id AND token_type = 'all'
                ) as is_blacklisted
            """
            result = await db.execute(text(query), {"user_id": user_id})
            result = result.mappings().first()

            if result and result["is_blacklisted"]:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User has been logged out of all sessions",
                )

        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error decoding token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


async def get_current_user(
    db, credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Get the currently authenticated user from the database.
    This function is used as a dependency for protected routes.

    Args:
        db: Database connection
        credentials: HTTP Authorization credentials

    Returns:
        User data as a dictionary

    Raises:
        HTTPException: If authentication fails
    """
    try:
        payload = await decode_token(credentials.credentials, db)

        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type for getting user",
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
            )

        # Fetch full user object from database
        query = """
            SELECT id, email, first_name, last_name, picture_url, memory,
                   created_at, updated_at, last_login_at
            FROM users
            WHERE id = :user_id AND deleted_at IS NULL
        """
        result = await db.execute(text(query), {"user_id": int(user_id)})
        user = result.mappings().first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
            )

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_current_user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed"
        )


async def blacklist_token(
    db, token: str, user_id: int, token_type: str, expires_at: datetime
) -> None:
    """
    Add a token to the blacklist.

    Args:
        db: Database connection
        token: The JWT token to blacklist
        user_id: The user ID the token belongs to
        token_type: The type of token (access or refresh)
        expires_at: When the token expires

    Raises:
        HTTPException: If database operation fails
    """
    try:
        query = """
            INSERT INTO token_blacklist (
                token, user_id, token_type, expires_at, blacklisted_at
            )
            VALUES (
                :token, :user_id, :token_type, :expires_at, :blacklisted_at
            )
            ON CONFLICT (token) DO NOTHING
        """

        await db.execute(
            text(query),
            {
                "token": token,
                "user_id": user_id,
                "token_type": token_type,
                "expires_at": expires_at,
                "blacklisted_at": datetime.now(timezone.utc),
            },
        )
    except Exception as e:
        logger.error(f"Error blacklisting token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to log out",
        )


async def is_token_blacklisted(db, token: str) -> bool:
    """
    Check if a token is blacklisted.

    Args:
        db: Database connection
        token: The JWT token to check

    Returns:
        True if token is blacklisted, False otherwise
    """
    try:
        query = """
            SELECT EXISTS(
                SELECT 1 FROM token_blacklist 
                WHERE token = :token
            ) as is_blacklisted
        """
        result = await db.execute(text(query), {"token": token})
        result = result.mappings().first()
        return result["is_blacklisted"] if result else False
    except Exception as e:
        logger.error(f"Error checking blacklisted token: {str(e)}")
        # If we can't check, assume it's not blacklisted
        return False


async def blacklist_user_tokens(db, user_id: int) -> None:
    """
    Add all tokens for a user to the blacklist.
    This won't actually find all tokens since they're stored client-side,
    but it will mark any tokens this user tries to verify in the future as invalid.

    Args:
        db: Database connection
        user_id: The user ID to blacklist tokens for

    Raises:
        HTTPException: If database operation fails
    """
    try:
        # Add a special record that marks all tokens for this user as invalid
        # We'll use the empty string as a special value
        query = """
            INSERT INTO token_blacklist (
                token, user_id, token_type, expires_at, blacklisted_at
            )
            VALUES (
                :token, :user_id, 'all', :expires_at, :blacklisted_at
            )
            ON CONFLICT (token) DO UPDATE 
            SET blacklisted_at = :blacklisted_at
        """

        # Set a far future expiration date
        expires_at = datetime.now(timezone.utc) + timedelta(days=3650)  # 10 years

        await db.execute(
            text(query),
            {
                "token": f"user:{user_id}:all",
                "user_id": user_id,
                "expires_at": expires_at,
                "blacklisted_at": datetime.now(timezone.utc),
            },
        )
    except Exception as e:
        logger.error(f"Error blacklisting user tokens: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to log out all sessions",
        )


async def cleanup_expired_blacklisted_tokens(db) -> int:
    """
    Remove expired tokens from the blacklist to keep the table size manageable.
    This should be run periodically, e.g., via a background task or cron job.

    Args:
        db: Database connection

    Returns:
        Number of tokens removed

    Raises:
        Exception: If database operation fails
    """
    try:
        query = """
            DELETE FROM token_blacklist
            WHERE expires_at < :now
            AND token_type != 'all'  -- Keep the "all tokens" entries
            RETURNING id
        """
        result = await db.execute(text(query), {"now": datetime.now(timezone.utc)})
        rows = result.mappings().all()

        count = len(rows)
        logger.info(f"Removed {count} expired tokens from blacklist")
        return count
    except Exception as e:
        logger.error(f"Error cleaning up blacklisted tokens: {str(e)}")
        raise
