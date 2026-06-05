import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import User
from app.core.config import settings
from app.core.security import verify_telegram_init_data, create_access_token

logger = logging.getLogger(__name__)
router = APIRouter()

class TelegramLoginSchema(BaseModel):
    initData: str

@router.post("/telegram/login")
async def telegram_login(payload: TelegramLoginSchema, db: AsyncSession = Depends(get_db)):
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
    else:
        logger.info(f"Authenticated existing user {telegram_id} via Telegram WebApp login.")
        
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
