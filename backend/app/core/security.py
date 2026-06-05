import hmac
import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from urllib.parse import parse_qsl
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.session import get_db
from app.db.models import User

logger = logging.getLogger(__name__)

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

security_scheme = HTTPBearer()

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Generate a signed JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_access_token(token: str) -> dict | None:
    """Decode and verify a JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.debug(f"JWT decode failed: {e}")
        return None

def verify_telegram_init_data(init_data: str, bot_token: str) -> dict | None:
    """
    Verify Telegram WebApp initData cryptographic signature.
    Returns the parsed query dict if valid, else None.
    """
    try:
        # 1. Parse query parameters
        params = dict(parse_qsl(init_data))
        if "hash" not in params:
            logger.warning("Missing hash in telegram init data.")
            return None
        
        received_hash = params.pop("hash")
        
        # SECURITY: Never allow dummy hash bypass in production
        if received_hash == "dummy":
            if settings.APP_ENV == "production":
                logger.critical("SECURITY: Dummy hash auth attempt blocked in production!")
                return None
            if settings.APP_ENV == "development":
                logger.info("Bypassing Telegram signature check for local development dev login.")
                return params
        
        # 2. Sort key-value pairs alphabetically and build data_check_string
        sorted_params = sorted(params.items())
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted_params)
        
        # 3. Calculate secret key — per Telegram docs: HMAC_SHA256(bot_token, "WebAppData")
        secret_key = hmac.new(bot_token.encode(), b"WebAppData", hashlib.sha256).digest()
        
        # 4. Calculate signature
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        logger.debug(f"Telegram Auth: data_check_string:\n{data_check_string}")
        logger.debug(f"Telegram Auth: calculated_hash={calculated_hash}")
        
        if calculated_hash != received_hash:
            logger.warning("Telegram signature verification failed.")
            return None
            
        return params
    except Exception as e:
        logger.error(f"Error validating Telegram signature: {e}")
        return None

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Dependency to retrieve the currently authenticated User."""
    token = credentials.credentials
    payload = verify_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject format invalid.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    try:
        stmt = select(User).where(User.id == user_uuid)
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Error querying user from token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection failed."
        )
        
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user profile.",
        )
        
    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db)
) -> User | None:
    """Optional authentication dependency that does not raise an error if token is missing/invalid."""
    if not credentials:
        return None
    token = credentials.credentials
    payload = verify_access_token(token)
    if not payload:
        return None
    user_id_str = payload.get("sub")
    if not user_id_str:
        return None
    try:
        user_uuid = uuid.UUID(user_id_str)
        stmt = select(User).where(User.id == user_uuid)
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        if user and user.is_active:
            return user
    except Exception:
        pass
    return None
