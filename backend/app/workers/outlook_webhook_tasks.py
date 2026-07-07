import logging
import httpx
from datetime import datetime, timezone, timedelta
from celery import shared_task
from sqlalchemy import select, or_, and_

from app.db.session import AsyncSessionLocal
from app.db.models import MailAccount, User, OutlookSubscription
from app.services.token_service import get_valid_access_token
from app.services.microsoft_sync import MicrosoftSyncService
from app.core.telemetry import telemetry
from app.workers.sync_tasks import async_to_sync

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="outlook_webhooks",
    name="app.workers.outlook_webhook_tasks.process_outlook_notification",
)
@async_to_sync
async def process_outlook_notification(self, subscription_id: str, message_id: str):
    """
    Process a single incoming Outlook message via Graph webhook.
    """
    async with AsyncSessionLocal() as db:
        # Find subscription and associated account
        stmt = select(OutlookSubscription).where(
            OutlookSubscription.subscription_id == subscription_id,
            OutlookSubscription.status == "active",
        )
        sub = (await db.execute(stmt)).scalar_one_or_none()
        
        if not sub:
            logger.warning("No active subscription found for %s", subscription_id)
            return
            
        account = await db.get(MailAccount, sub.mail_account_id)
        if not account or account.status == "disconnected":
            logger.warning("Account disconnected for subscription %s", subscription_id)
            return

        # Fetch user's telegram ID
        stmt = select(User.telegram_id).where(User.id == account.user_id)
        telegram_id = (await db.execute(stmt)).scalar_one()

        # Get valid access token
        try:
            access_token = await get_valid_access_token(account, db)
        except Exception as e:
            logger.error("Failed to get access token for account %s: %s", account.id, e)
            raise self.retry(exc=e)

        # Fetch the specific message from Graph
        url = f"https://graph.microsoft.com/v1.0/me/messages/{message_id}"
        params = {
            "$select": "id,subject,from,receivedDateTime,bodyPreview,hasAttachments,isRead"
        }
        
        transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0")
        async with httpx.AsyncClient(transport=transport, timeout=30.0) as client:
            resp = await client.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if resp.status_code == 404:
                logger.info("Message %s not found (likely deleted before processing).", message_id)
                return
            elif resp.status_code != 200:
                raise ValueError(f"Graph API fetch failed: HTTP {resp.status_code}")

            msg = resp.json()

        # Reuse existing sync logic to handle dedup, notifications, and forwarding
        service = MicrosoftSyncService(account, db)
        await service.process_single_message(msg, telegram_id)
        await db.commit()


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    queue="outlook_webhooks",
    name="app.workers.outlook_webhook_tasks.renew_expiring_outlook_subscriptions",
)
@async_to_sync
async def renew_expiring_outlook_subscriptions(self):
    """
    Beat task to renew Graph subscriptions before they expire.
    """
    now = datetime.now(timezone.utc)
    renewal_window = now + timedelta(hours=24)
    renewed = 0
    failed = 0
    
    async with AsyncSessionLocal() as db:
        # Find subscriptions expiring within 24h OR that are in 'failed' state
        stmt = select(OutlookSubscription).where(
            or_(
                and_(OutlookSubscription.status == "active", OutlookSubscription.expiration_datetime <= renewal_window),
                OutlookSubscription.status == "failed",
            )
        )
        result = await db.execute(stmt)
        subs = result.scalars().all()
        
        if not subs:
            return

        for sub in subs:
            stmt_acc = select(MailAccount).where(MailAccount.id == sub.mail_account_id)
            account = (await db.execute(stmt_acc)).scalar_one_or_none()
            
            if account is None or account.status == "disconnected":
                sub.status = "cancelled"
                await db.commit()
                continue
                
            try:
                access_token = await get_valid_access_token(account, db)
                new_expiry = datetime.now(timezone.utc) + timedelta(minutes=4200)
                
                transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0")
                async with httpx.AsyncClient(transport=transport, timeout=30.0) as client:
                    resp = await client.patch(
                        f"https://graph.microsoft.com/v1.0/subscriptions/{sub.subscription_id}",
                        json={"expirationDateTime": new_expiry.strftime("%Y-%m-%dT%H:%M:%S.0000000Z")},
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                    
                if resp.status_code == 404:
                    sub.status = "expired"
                    sub.last_error = "Graph returned 404 on renewal — subscription no longer exists"
                elif resp.status_code == 200:
                    sub.expiration_datetime = new_expiry
                    sub.renewed_at = datetime.now(timezone.utc)
                    sub.last_error = None
                    sub.status = "active"
                    renewed += 1
                else:
                    sub.last_error = f"HTTP {resp.status_code}"
                    sub.status = "failed"
                    failed += 1
                await db.commit()
            except Exception as e:
                sub.last_error = str(e)[:500]
                sub.status = "failed"
                await db.commit()
                failed += 1
                logger.error("Renewal failed for subscription %s: %s", sub.subscription_id, e)

        await telemetry.log_event(
            db=db, 
            service="worker_outlook_webhooks", 
            event_type="Subscription Renewal Batch",
            metadata_payload={"total": len(subs), "renewed": renewed, "failed": failed},
        )
