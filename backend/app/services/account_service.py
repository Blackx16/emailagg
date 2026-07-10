from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.models import User, MailAccount
from app.core.encryption import encrypt_token
from app.services.outlook_subscription_service import cancel_subscription

async def find_or_create_oauth_account(
    telegram_id: int,
    provider: str,
    email: str,
    access_token: str,
    refresh_token: str,
    expires_in: int,
    db: AsyncSession,
) -> tuple[str, str]:
    """Find or create a User, verify account limits, and save the MailAccount.
    Returns:
        tuple: (user_id, account_id)
    """
    # Find or create User based on Telegram ID
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(telegram_id=telegram_id, plan="free")
        db.add(user)
        await db.flush()  # Populate user.id

    # Check if this account is already registered for this user
    stmt_existing = select(MailAccount).where(
        MailAccount.user_id == user.id,
        MailAccount.provider == provider,
        MailAccount.email == email
    )
    result_existing = await db.execute(stmt_existing)
    existing_account = result_existing.scalar_one_or_none()

    if not existing_account:
        # Check active accounts count directly using func.count() to avoid loading all ORM objects
        stmt_count = select(func.count()).select_from(MailAccount).where(
            MailAccount.user_id == user.id,
            MailAccount.status != "disconnected"
        )
        active_accounts_count = (await db.execute(stmt_count)).scalar_one()

        if active_accounts_count >= user.max_accounts:
            raise HTTPException(
                status_code=403,
                detail=f"Account limit reached ({user.max_accounts}) for your '{user.plan}' plan. Please upgrade to connect more.",
            )

        # Create new MailAccount
        new_account = MailAccount(
            user_id=user.id,
            provider=provider,
            email=email,
            access_token_encrypted=encrypt_token(access_token),
            refresh_token_encrypted=encrypt_token(refresh_token) if refresh_token else None,
            token_expires_at=datetime.now(timezone.utc) + timedelta(seconds=expires_in),
            status="active",
        )
        db.add(new_account)
        await db.commit()
        await db.refresh(new_account)
        account_id = new_account.id
    else:
        # Update existing account's credentials and reactivate
        existing_account.access_token_encrypted = encrypt_token(access_token)
        if refresh_token:
            existing_account.refresh_token_encrypted = encrypt_token(refresh_token)
        existing_account.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        existing_account.status = "active"
        existing_account.error_message = None
        existing_account.notify_telegram = True
        existing_account.deliver_to_dashboard = True
        existing_account.forward_enabled = True
        await db.commit()
        account_id = existing_account.id

    return user.id, account_id

async def deactivate_mail_account(account: MailAccount, db: AsyncSession) -> None:
    """Safely deactivate a mail account and clean up external resources."""
    if account.provider == "microsoft":
        await cancel_subscription(account, db)
        
    account.status = "disconnected"
    account.access_token_encrypted = None
    account.refresh_token_encrypted = None
    account.token_expires_at = None
    await db.commit()
