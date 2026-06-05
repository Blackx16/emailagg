from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.db.session import get_db
from app.db.models import User

router = APIRouter()


class UserRegisterSchema(BaseModel):
    telegram_id: int
    email: str | None = None


@router.post("/register")
async def register_user(payload: UserRegisterSchema, db: AsyncSession = Depends(get_db)):
    """Register a new user via Telegram ID if they do not exist."""
    stmt = select(User).where(User.telegram_id == payload.telegram_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(telegram_id=payload.telegram_id, email=payload.email, plan="free")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return {
            "status": "success",
            "message": "User registered successfully.",
            "user_id": str(user.id),
        }
    else:
        return {
            "status": "success",
            "message": "User already registered.",
            "user_id": str(user.id),
        }
