from datetime import datetime, timezone, timedelta
import html
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.db.models import User, MailAccount
from app.core.encryption import encrypt_token
from app.core.limiter import limiter
from app.core.redis import get_redis
from app.services import microsoft_auth, google_auth
from app.services.account_service import find_or_create_oauth_account, deactivate_mail_account
from app.services.outlook_subscription_service import create_subscription
from app.workers.sync_tasks import sync_account
from app.workers.notification_tasks import send_telegram_message
from app.core.telemetry import telemetry

router = APIRouter()

@router.get("/microsoft/login")
@limiter.limit("10/minute")
async def microsoft_login(request: Request, telegram_id: int):
    """Initiate Microsoft Outlook OAuth login."""
    url = await microsoft_auth.get_login_url(telegram_id)
    return RedirectResponse(url)


@router.get("/microsoft/callback")
async def microsoft_callback(code: str, state: str, db: AsyncSession = Depends(get_db)):
    """Callback for Microsoft Outlook OAuth authentication."""
    # Validate state token from Redis (CSRF protection)
    redis = await get_redis()
    telegram_id_str = await redis.get(f"oauth_state:{state}")
    if not telegram_id_str:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state token.")
    await redis.delete(f"oauth_state:{state}")  # One-time use
    telegram_id = int(telegram_id_str)

    try:
        token_data = await microsoft_auth.exchange_code(code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth exchange failed: {str(e)}")

    return await register_oauth_account(
        telegram_id=telegram_id,
        provider="microsoft",
        email=token_data["email"],
        access_token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        expires_in=token_data["expires_in"],
        db=db,
    )


@router.get("/google/login")
@limiter.limit("10/minute")
async def google_login(request: Request, telegram_id: int):
    """Initiate Google Gmail OAuth login."""
    url = await google_auth.get_login_url(telegram_id)
    return RedirectResponse(url)


@router.get("/google/callback")
async def google_callback(code: str, state: str, db: AsyncSession = Depends(get_db)):
    """Callback for Google Gmail OAuth authentication."""
    # Validate state token from Redis (CSRF protection)
    redis = await get_redis()
    telegram_id_str = await redis.get(f"oauth_state:{state}")
    if not telegram_id_str:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state token.")
    await redis.delete(f"oauth_state:{state}")  # One-time use
    telegram_id = int(telegram_id_str)

    try:
        token_data = await google_auth.exchange_code(code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth exchange failed: {str(e)}")

    return await register_oauth_account(
        telegram_id=telegram_id,
        provider="google",
        email=token_data["email"],
        access_token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        expires_in=token_data["expires_in"],
        db=db,
    )


from pydantic import BaseModel

class IMAPConnectSchema(BaseModel):
    email: str
    password: str
    imap_host: str
    imap_port: int = 993


from app.core.security import get_current_user


@router.post("/imap/connect")
@limiter.limit("10/minute")
async def connect_imap(
    request: Request,
    payload: IMAPConnectSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Connect a custom IMAP mail account."""
    # 1. Check if this account is already registered for this user
    stmt_existing = select(MailAccount).where(
        MailAccount.user_id == current_user.id,
        MailAccount.provider == "imap",
        MailAccount.email == payload.email
    )
    result_existing = await db.execute(stmt_existing)
    existing_account = result_existing.scalar_one_or_none()

    if not existing_account:
        # Check active accounts count directly using func.count() to avoid loading all ORM objects
        stmt_count = select(func.count()).select_from(MailAccount).where(
            MailAccount.user_id == current_user.id,
            MailAccount.status != "disconnected"
        )
        active_accounts_count = (await db.execute(stmt_count)).scalar_one()

        if active_accounts_count >= current_user.max_accounts:
            raise HTTPException(
                status_code=403,
                detail=f"Account limit reached ({current_user.max_accounts}) for your '{current_user.plan}' plan. Please upgrade to connect more.",
            )

        new_account = MailAccount(
            user_id=current_user.id,
            provider="imap",
            email=payload.email,
            access_token_encrypted=encrypt_token(payload.password),
            imap_host=payload.imap_host,
            imap_port=payload.imap_port,
            status="active",
        )
        db.add(new_account)
        await db.commit()
        await db.refresh(new_account)
        account_id = new_account.id
    else:
        existing_account.access_token_encrypted = encrypt_token(payload.password)
        existing_account.imap_host = payload.imap_host
        existing_account.imap_port = payload.imap_port
        existing_account.status = "active"
        existing_account.notify_telegram = True
        existing_account.deliver_to_dashboard = True
        existing_account.forward_enabled = True
        existing_account.error_message = None
        await db.commit()
        account_id = existing_account.id

    await telemetry.log_event(
        db=db,
        service="api",
        event_type="Mailbox Connected",
        user_id=current_user.id,
        metadata_payload={"provider": "imap", "email": payload.email}
    )

    # 3. Trigger async initial sync
    sync_account.delay(str(account_id))

    return {
        "status": "success",
        "message": "IMAP account connected successfully.",
        "account_id": str(account_id)
    }


@router.post("/disconnect/{account_id}")
async def disconnect_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Disconnect a mail account and revoke local tokens."""
    try:
        acc_uuid = uuid.UUID(account_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid account UUID format.")

    stmt = select(MailAccount).where(
        MailAccount.id == acc_uuid,
        MailAccount.user_id == current_user.id
    )
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Mail account not found or access denied.")

    await deactivate_mail_account(account, db)

    return {"status": "success", "message": "Account disconnected successfully."}


async def register_oauth_account(
    telegram_id: int,
    provider: str,
    email: str,
    access_token: str,
    refresh_token: str,
    expires_in: int,
    db: AsyncSession,
):
    """Core logic to exchange code, get user info, and store the account in DB."""
    user_id, account_id = await find_or_create_oauth_account(
        telegram_id=telegram_id,
        provider=provider,
        email=email,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        db=db,
    )

    await telemetry.log_event(
        db=db,
        service="api",
        event_type="Mailbox Connected",
        user_id=user_id,
        metadata_payload={"provider": provider, "email": email}
    )

    if provider == "microsoft":
        # Resolve the MailAccount object since create_subscription needs it
        account = await db.get(MailAccount, account_id)
        if account:
            await create_subscription(account, db)

    # Trigger async initial sync
    sync_account.delay(str(account_id))

    # Send confirmation message to user via Telegram bot
    try:
        await send_telegram_message(
            telegram_id,
            f"✅ <b>{provider.capitalize()}</b> account (<code>{email}</code>) connected successfully!\n\n"
            f"📬 Syncing your inbox now — you'll get notifications for new emails."
        )
    except Exception:
        pass  # Don't fail the OAuth flow if notification fails

    safe_provider = html.escape(provider.capitalize() if provider else "Unknown")
    safe_email = html.escape(email if email else "Unknown")

    return HTMLResponse(
        content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Account Connected</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                background-color: #f3f4f6;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
            }}
            .card {{
                background-color: white;
                padding: 2.5rem;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                text-align: center;
                max-width: 400px;
            }}
            h1 {{ color: #10b981; margin-bottom: 1rem; }}
            p {{ color: #4b5563; line-height: 1.5; }}
            .email {{ color: #3b82f6; font-weight: 600; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Success!</h1>
            <p>Your {safe_provider} account (<span class="email">{safe_email}</span>) has been connected successfully.</p>
            <p>You can close this window now and return to your Telegram bot.</p>
        </div>
    </body>
    </html>
    """
    )
