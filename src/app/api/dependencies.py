"""API dependencies for authentication and authorization."""

import logging
from typing import Optional

from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.settings import settings

logger = logging.getLogger(__name__)

# OAuth2 Bearer token security scheme
security = HTTPBearer()


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Verify JWT token from Authorization header.
    
    This dependency validates the JWT token and extracts the payload.
    Use this as a dependency in route handlers to enforce authentication.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        dict: Decoded JWT payload
        
    Raises:
        HTTPException: 401 if token is invalid, expired, or missing required claims
    """
    token = credentials.credentials
    secret_key = settings.get_jwt_secret_key()
    
    if not secret_key:
        logger.error(
            "JWT secret key not configured - authentication cannot be validated",
            extra={"recommendation": "Set JWT_SECRET_KEY environment variable"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication service not properly configured",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Decode and validate JWT token
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        
        # Validate required claims
        if "sub" not in payload and "client_id" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing required claims (sub or client_id)",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.debug(
            "Token validated successfully",
            extra={"client_id": payload.get("client_id") or payload.get("sub")}
        )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTClaimsError as e:
        logger.warning(f"Token claims invalid: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token claims invalid: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        logger.warning(f"Token validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_client_id(token_payload: dict = Depends(verify_token)) -> str:
    """
    Extract client_id from validated token.
    
    Use this dependency when you need the client_id in your route handler.
    
    Args:
        token_payload: Validated JWT payload from verify_token dependency
        
    Returns:
        str: Client ID from token (from 'client_id' or 'sub' claim)
    """
    return token_payload.get("client_id") or token_payload.get("sub")
