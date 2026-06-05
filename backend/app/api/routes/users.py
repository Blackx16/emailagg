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


@router.get("/profile")
async def get_user_profile(telegram_id: int, db: AsyncSession = Depends(get_db)):
    """Return user profile info for the Telegram bot /settings command."""
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not registered.")

    # Count connected accounts
    from app.db.models import MailAccount

    stmt_accounts = select(MailAccount).where(MailAccount.user_id == user.id)
    res_accounts = await db.execute(stmt_accounts)
    accounts = res_accounts.scalars().all()

    connected_accounts = len(accounts)
    active_accounts = sum(1 for a in accounts if a.status != "disconnected")

    return {
        "plan": user.plan,
        "max_accounts": user.max_accounts,
        "connected_accounts": connected_accounts,
        "active_accounts": active_accounts,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }

