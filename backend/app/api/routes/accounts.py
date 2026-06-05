from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import User, MailAccount
from app.core.security import get_current_user_optional

router = APIRouter()


@router.get("")
async def get_user_accounts(
    telegram_id: int | None = Query(None),
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve connected email accounts for a user (via JWT or Telegram ID)."""
    if current_user:
        user = current_user
    elif telegram_id is not None:
        stmt_user = select(User).where(User.telegram_id == telegram_id)
        res_user = await db.execute(stmt_user)
        user = res_user.scalar_one_or_none()
    else:
        raise HTTPException(status_code=400, detail="Authentication required or telegram_id query parameter missing.")

    if not user:
        raise HTTPException(status_code=404, detail="User not registered.")

    # Find mail accounts for this user
    stmt_accounts = select(MailAccount).where(MailAccount.user_id == user.id)
    res_accounts = await db.execute(stmt_accounts)
    accounts = res_accounts.scalars().all()

    return [
        {
            "id": str(acc.id),
            "provider": acc.provider,
            "email": acc.email,
            "status": acc.status,
            "last_sync": acc.last_sync.isoformat() if acc.last_sync else None,
            "error_message": acc.error_message,
        }
        for acc in accounts
    ]
