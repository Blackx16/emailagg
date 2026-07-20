import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import User
from app.core.config import settings
from app.core.security import verify_telegram_init_data, create_access_token
from app.core.limiter import limiter
from app.core.telemetry import telemetry

logger = logging.getLogger(__name__)
router = APIRouter()

class TelegramLoginSchema(BaseModel):
    initData: str

@router.post("/telegram/login")
@limiter.limit("20/minute")
async def telegram_login(payload: TelegramLoginSchema, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Authenticate a user via Telegram WebApp initData query string.
    Verifies the cryptographic signature and issues a JWT access token.
    """
    # 1. Verify Telegram signature
    params = verify_telegram_init_data(payload.initData, settings.TELEGRAM_BOT_TOKEN)
    if not params:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram signature."
        )
        
    # 2. Extract user info
    user_str = params.get("user")
    if not user_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing user field in Telegram initData."
        )
        
    try:
        user_data = json.loads(user_str)
        telegram_id = int(user_data["id"])
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
        logger.error(f"Error parsing Telegram user data JSON: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user data format inside Telegram initData."
        )
        
    # 3. Find or register user
    stmt = select(User).where(User.telegram_id == telegram_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    
    if not user:
        # Register new user dynamically
        username = user_data.get("username", "")
        # Store username or details if needed. Let's register basic user.
        user = User(telegram_id=telegram_id, plan="free", is_active=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info(f"Registered new user {telegram_id} via Telegram WebApp login.")
        await telemetry.log_event(
            db=db,
            service="api",
            event_type="User Signup",
            user_id=user.id,
            metadata_payload={"plan": user.plan},
        )
    else:
        logger.info(f"Authenticated existing user {telegram_id} via Telegram WebApp login.")
        await telemetry.log_event(
            db=db,
            service="api",
            event_type="User Login",
            user_id=user.id,
            metadata_payload={},
        )
        
    # 4. Generate JWT access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "telegram_id": user.telegram_id,
            "email": user.email,
            "plan": user.plan
        }
    }


class DevBypassSchema(BaseModel):
    telegram_id: int
    bypass_key: str


@router.post("/telegram/dev-bypass")
@limiter.limit("5/minute")
async def dev_bypass_login(payload: DevBypassSchema, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Developer bypass login: authenticate by telegram_id + a secret bypass key.
    This avoids the need for Telegram initData signature.
    Protected by the INTERNAL_API_KEY.
    """
    import hmac as _hmac

    if not settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=500, detail="Server misconfigured.")

    if not _hmac.compare_digest(payload.bypass_key, settings.INTERNAL_API_KEY):
        logger.warning(f"Dev bypass attempt with invalid key for telegram_id={payload.telegram_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid bypass key."
        )

    stmt = select(User).where(User.telegram_id == payload.telegram_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No user found with telegram_id {payload.telegram_id}."
        )

    logger.info(f"Dev bypass login for user {user.id} (telegram_id={payload.telegram_id})")

    access_token = create_access_token(data={"sub": str(user.id)})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "telegram_id": user.telegram_id,
            "email": user.email,
            "plan": user.plan
        }
    }
