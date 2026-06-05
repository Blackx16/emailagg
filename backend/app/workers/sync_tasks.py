import logging
import asyncio
from functools import wraps
from celery import shared_task
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.db.models import MailAccount

logger = logging.getLogger(__name__)


def async_to_sync(func):
    """Decorator to run async functions inside synchronous Celery tasks."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            return asyncio.run_coroutine_threadsafe(func(*args, **kwargs), loop).result()
        else:
            return loop.run_until_complete(func(*args, **kwargs))
    return wrapper


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
@async_to_sync
async def poll_all_accounts(self):
    """
    Beat-scheduled task.
    Queries active mailboxes and enqueues sync tasks.
    """
    logger.info("poll_all_accounts triggered")
    async with AsyncSessionLocal() as db:
        # Fetch accounts that are not disconnected
        stmt = select(MailAccount.id).where(MailAccount.status != "disconnected")
        result = await db.execute(stmt)
        account_ids = result.scalars().all()

        for account_id in account_ids:
            sync_account.delay(str(account_id))


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
@async_to_sync
async def sync_account(self, account_id: str):
    """
    Synchronizes emails for a single mail account.
    """
    logger.info("sync_account called for %s", account_id)
    async with AsyncSessionLocal() as db:
        # Load mailbox account
        stmt = select(MailAccount).where(MailAccount.id == account_id)
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()

        if not account or account.status == "disconnected":
            logger.warning(f"MailAccount {account_id} not found or disconnected. Skipping.")
            return

        # Mark account status as syncing
        account.status = "syncing"
        await db.commit()

        try:
            if account.provider == "microsoft":
                from app.services.microsoft_sync import MicrosoftSyncService
                service = MicrosoftSyncService(account, db)
                await service.sync()
            elif account.provider == "google":
                from app.services.gmail_sync import GmailSyncService
                service = GmailSyncService(account, db)
                await service.sync()
            elif account.provider == "imap":
                from app.services.imap_sync import IMAPSyncService
                service = IMAPSyncService(account, db)
                await service.sync()
            else:
                raise ValueError(f"Unknown mail provider: {account.provider}")
        except Exception as exc:
            logger.error("sync_account failed for %s: %s", account_id, exc)
            # Re-fetch database session data to prevent transaction state failures
            account.status = "error"
            account.error_message = str(exc)
            await db.commit()
            raise self.retry(exc=exc)
