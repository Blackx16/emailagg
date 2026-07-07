from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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

    # Retrieve existing connected accounts
    stmt_accounts = select(MailAccount).where(MailAccount.user_id == user.id)
    result_accounts = await db.execute(stmt_accounts)
    accounts = result_accounts.scalars().all()

    # Check if this account is already registered for this user
    existing_account = next(
        (a for a in accounts if a.provider == provider and a.email == email), None
    )

    if not existing_account:
        active_accounts_count = sum(1 for a in accounts if a.status != "disconnected")
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
