import logging
import secrets
from datetime import datetime, timezone, timedelta
import httpx
from sqlalchemy import select

from app.core.config import settings
from app.core.encryption import encrypt_token
from app.db.models import MailAccount, OutlookSubscription
from app.services.token_service import get_valid_access_token
from app.core.redis import get_redis

logger = logging.getLogger(__name__)


async def create_subscription(account: MailAccount, db) -> OutlookSubscription | None:
    client_state = secrets.token_urlsafe(32)
    
    try:
        access_token = await get_valid_access_token(account, db)
    except Exception as e:
        logger.error("Failed to get valid access token during subscription creation: %s", e)
        return None

    notification_url = f"{settings.BACKEND_URL}/api/v1/webhooks/outlook"

    body = {
        "changeType": "created",
        "notificationUrl": notification_url,
        "resource": "me/mailFolders/inbox/messages",
        "expirationDateTime": (datetime.now(timezone.utc) + timedelta(minutes=4200)).strftime("%Y-%m-%dT%H:%M:%S.0000000Z"),
        "clientState": client_state,
    }
    
    transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0")
    async with httpx.AsyncClient(transport=transport, timeout=30.0) as client:
        resp = await client.post(
            "https://graph.microsoft.com/v1.0/subscriptions", 
            json=body,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if resp.status_code != 201:
            logger.error("Graph subscription creation failed for account %s: HTTP %s - %s", account.id, resp.status_code, resp.text)
            return None

        data = resp.json()

    sub = OutlookSubscription(
        mail_account_id=account.id,
        subscription_id=data["id"],
        client_state_encrypted=encrypt_token(client_state),
        expiration_datetime=datetime.fromisoformat(data["expirationDateTime"].replace("Z", "+00:00")),
        status="active",
    )
    db.add(sub)
    await db.commit()
    return sub


async def cancel_subscription(account: MailAccount, db) -> None:
    stmt = select(OutlookSubscription).where(
        OutlookSubscription.mail_account_id == account.id, 
        OutlookSubscription.status == "active"
    )
    sub = (await db.execute(stmt)).scalar_one_or_none()
    if sub is None:
        return
        
    try:
        access_token = await get_valid_access_token(account, db)
        transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0")
        async with httpx.AsyncClient(transport=transport, timeout=30.0) as client:
            resp = await client.delete(
                f"https://graph.microsoft.com/v1.0/subscriptions/{sub.subscription_id}",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if resp.status_code not in (204, 404):
                logger.warning("Graph subscription delete returned HTTP %s for %s", resp.status_code, sub.subscription_id)
    except ValueError:
        pass  # Token revoked or unavailable
        
    sub.status = "cancelled"
    await db.commit()
    
    # Clean up Redis
    redis = await get_redis()
    await redis.delete(f"outlook_sub_state:{sub.subscription_id}")
