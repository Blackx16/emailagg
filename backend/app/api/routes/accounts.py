from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import User, MailAccount
from app.core.security import get_current_user

router = APIRouter()


@router.get("")
async def get_user_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve connected email accounts for the authenticated user (JWT required)."""
    # Find mail accounts for this user
    stmt_accounts = select(MailAccount).where(MailAccount.user_id == current_user.id)
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


@router.get("/internal/by-telegram/{telegram_id}")
async def get_accounts_by_telegram_id(
    telegram_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Internal endpoint for the Telegram bot to list accounts by telegram_id.
    Only accessible from the internal Docker network."""
    stmt_user = select(User).where(User.telegram_id == telegram_id)
    res_user = await db.execute(stmt_user)
    user = res_user.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not registered.")

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


@router.post("/{account_id}/disconnect")
async def disconnect_account_internal(
    account_id: str,
    telegram_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Internal endpoint for the Telegram bot to disconnect a mail account via telegram_id."""
    import uuid as _uuid

    try:
        acc_uuid = _uuid.UUID(account_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid account UUID format.")

    # Resolve user from telegram_id
    stmt_user = select(User).where(User.telegram_id == telegram_id)
    res_user = await db.execute(stmt_user)
    user = res_user.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not registered.")

    # Find the account and verify ownership
    stmt_acc = select(MailAccount).where(
        MailAccount.id == acc_uuid,
        MailAccount.user_id == user.id,
    )
    res_acc = await db.execute(stmt_acc)
    account = res_acc.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Mail account not found or access denied.")

    email = account.email
    account.status = "disconnected"
    account.access_token_encrypted = None
    account.refresh_token_encrypted = None
    account.token_expires_at = None
    await db.commit()

    return {"status": "success", "message": "Account disconnected successfully.", "email": email}

