from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.db.session import get_db
from app.db.models import User
from app.core.security import verify_internal
from app.core.telemetry import telemetry

router = APIRouter()


class UserRegisterSchema(BaseModel):
    telegram_id: int
    email: str | None = None


@router.post("/register")
async def register_user(payload: UserRegisterSchema, db: AsyncSession = Depends(get_db), _internal: None = Depends(verify_internal)):
    """Register a new user via Telegram ID if they do not exist."""
    stmt = select(User).where(User.telegram_id == payload.telegram_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(telegram_id=payload.telegram_id, email=payload.email, plan="free")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        await telemetry.log_event(
            db=db,
            service="api",
            event_type="User Signup",
            user_id=user.id,
            metadata_payload={"telegram_id": payload.telegram_id, "plan": user.plan}
        )

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
async def get_user_profile(telegram_id: int, db: AsyncSession = Depends(get_db), _internal: None = Depends(verify_internal)):
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


# ── Notification preferences ──────────────────────────────────────────────────

import math
from app.core.security import get_current_user


def _compute_effective_limit(user_set: int, active_accounts: int) -> int:
    """
    Floor = max(5, ceil(active_accounts × 0.10)).
    Effective limit is whichever is higher: the user's setting or the floor.
    """
    floor = max(5, math.ceil(active_accounts * 0.1))
    return max(user_set, floor)


class NotificationPreferencesSchema(BaseModel):
    notification_limit_per_hour: int


@router.get("/me/preferences")
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the user's notification limit and the computed effective floor."""
    from app.db.models import MailAccount

    stmt_acc = select(MailAccount).where(
        MailAccount.user_id == current_user.id,
        MailAccount.status != "disconnected",
    )
    res_acc = await db.execute(stmt_acc)
    active_count = len(res_acc.scalars().all())

    floor = max(5, math.ceil(active_count * 0.1))
    effective = _compute_effective_limit(current_user.notification_limit_per_hour, active_count)

    return {
        "notification_limit_per_hour": current_user.notification_limit_per_hour,
        "effective_limit": effective,
        "floor": floor,
        "active_accounts": active_count,
    }


@router.put("/me/preferences")
async def update_notification_preferences(
    payload: NotificationPreferencesSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update the user's notification limit.
    The backend silently enforces a minimum of max(5, ceil(accounts × 0.1)).
    """
    from app.db.models import MailAccount

    if payload.notification_limit_per_hour < 1:
        raise HTTPException(status_code=400, detail="Limit must be at least 1.")

    stmt_acc = select(MailAccount).where(
        MailAccount.user_id == current_user.id,
        MailAccount.status != "disconnected",
    )
    res_acc = await db.execute(stmt_acc)
    active_count = len(res_acc.scalars().all())

    # Persist whatever the user asked for; effective_limit is computed at send time
    stmt_user = select(User).where(User.id == current_user.id)
    res_user = await db.execute(stmt_user)
    user_row = res_user.scalar_one()
    user_row.notification_limit_per_hour = payload.notification_limit_per_hour
    await db.commit()

    floor = max(5, math.ceil(active_count * 0.1))
    effective = _compute_effective_limit(payload.notification_limit_per_hour, active_count)

    await telemetry.log_event(
        db=db,
        service="api",
        event_type="Notification Limit Updated",
        user_id=current_user.id,
        metadata_payload={
            "limit_per_hour": payload.notification_limit_per_hour,
            "effective_limit": effective,
            "active_accounts": active_count,
        },
    )

    return {
        "status": "success",
        "notification_limit_per_hour": payload.notification_limit_per_hour,
        "effective_limit": effective,
        "floor": floor,
        "message": f"Effective limit is {effective}/hr (floor for {active_count} accounts = {floor}/hr).",
    }
