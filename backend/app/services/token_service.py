from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import MailAccount
from app.core.encryption import decrypt_token, encrypt_token


async def get_valid_access_token(account: MailAccount, db: AsyncSession) -> str:
    """
    Get a valid access token for the mail account.
    If the current access token is expired or close to expiring, it is automatically
    refreshed and saved to the database.
    """
    if account.provider == "imap":
        # IMAP stores the app password in access_token_encrypted
        return decrypt_token(account.access_token_encrypted)

    now = datetime.now(timezone.utc)
    is_expired = (
        account.token_expires_at is None
        or account.token_expires_at.replace(tzinfo=timezone.utc) <= now + timedelta(minutes=5)
    )

    if not is_expired:
        return decrypt_token(account.access_token_encrypted)

    # Token needs to be refreshed
    refresh_token = decrypt_token(account.refresh_token_encrypted)

    try:
        if account.provider == "microsoft":
            from app.services.microsoft_auth import refresh_tokens
            new_tokens = await refresh_tokens(refresh_token)
        elif account.provider == "google":
            from app.services.google_auth import refresh_tokens
            new_tokens = await refresh_tokens(refresh_token)
        else:
            raise ValueError(f"Unknown OAuth provider: {account.provider}")
    except Exception as e:
        account.status = "error"
        account.error_message = f"Token refresh failed: {str(e)[:500]}"
        await db.commit()
        raise e

    # Update tokens in DB
    account.access_token_encrypted = encrypt_token(new_tokens["access_token"])
    if "refresh_token" in new_tokens and new_tokens["refresh_token"]:
        account.refresh_token_encrypted = encrypt_token(new_tokens["refresh_token"])

    expires_in = new_tokens.get("expires_in", 3600)
    account.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    account.status = "active"
    account.error_message = None

    await db.commit()
    return new_tokens["access_token"]
