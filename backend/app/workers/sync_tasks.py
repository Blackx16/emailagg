import math
import random
import logging
import asyncio
import time
from functools import wraps
from celery import shared_task
from sqlalchemy import select
import redis as redis_lib

from app.db.session import AsyncSessionLocal
from app.db.models import MailAccount
from app.core.config import settings
from app.core.telemetry import telemetry

logger = logging.getLogger(__name__)

# Redis client for sync task deduplication locks
_sync_redis = redis_lib.from_url(settings.REDIS_URL)


def async_to_sync(func):
    """Decorator to run async functions inside synchronous Celery tasks."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))
    return wrapper


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    queue="maintenance",
    name="app.workers.sync_tasks.orchestrate_accounts",
)
@async_to_sync
async def orchestrate_accounts(self):
    """
    Beat-scheduled orchestrator task.

    Queries all non-disconnected mail accounts and distributes individual
    sync tasks evenly across the SYNC_POLL_INTERVAL window with a small
    random jitter.  This prevents a thundering herd at t=0 and makes load
    self-scaling: adding more accounts spreads them further without any
    config change.

    Example (300 s window, 12 000 accounts):
        Account 0    → countdown = 0.0 s ± jitter
        Account 1    → countdown = 0.025 s ± jitter
        Account N-1  → countdown = ~299.9 s ± jitter
    """
    poll_interval = settings.SYNC_POLL_INTERVAL

    async with AsyncSessionLocal() as db:
        stmt = select(MailAccount.id).where(MailAccount.status != "disconnected")
        result = await db.execute(stmt)
        account_ids = result.scalars().all()

    total = len(account_ids)
    if not total:
        logger.info("orchestrate_accounts: no active accounts — skipping.")
        return

    jitter_max = min(10.0, poll_interval / total / 2) if total > 1 else 0.0

    for i, account_id in enumerate(account_ids):
        # Evenly spread within the window
        base_delay = (i / total) * poll_interval
        jitter = random.uniform(-jitter_max, jitter_max)
        countdown = max(0.0, base_delay + jitter)

        sync_account.apply_async(
            args=[str(account_id)],
            countdown=countdown,
            queue="sync",
        )

    logger.info(
        "orchestrate_accounts: dispatched %d sync tasks across %ds window.",
        total,
        poll_interval,
    )


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    queue="sync",
    name="app.workers.sync_tasks.sync_account",
)
@async_to_sync
async def sync_account(self, account_id: str):
    """
    Synchronises emails for a single mail account.
    Uses a Redis lock to prevent concurrent syncs of the same account.
    """
    lock_key = f"sync_lock:{account_id}"
    lock = _sync_redis.lock(lock_key, timeout=300)  # 5-min lock timeout

    if not lock.acquire(blocking=False):
        logger.info("Sync already running for %s — skipping duplicate.", account_id)
        return

    try:
        async with AsyncSessionLocal() as db:
            stmt = select(MailAccount).where(MailAccount.id == account_id)
            result = await db.execute(stmt)
            account = result.scalar_one_or_none()

            if not account or account.status == "disconnected":
                logger.warning("MailAccount %s not found or disconnected — skipping.", account_id)
                return

            account.status = "syncing"
            await db.commit()

            try:
                start_time = time.time()
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
                    raise ValueError(f"Unknown provider: {account.provider}")

                duration_ms = int((time.time() - start_time) * 1000)
                await telemetry.log_event(
                    db=db,
                    service="worker_sync",
                    event_type="Sync Completed",
                    user_id=account.user_id,
                    worker=self.request.hostname,
                    duration_ms=duration_ms,
                    metadata_payload={"account_id": account_id, "provider": account.provider}
                )

            except Exception as exc:
                duration_ms = int((time.time() - start_time) * 1000)
                await telemetry.log_event(
                    db=db,
                    service="worker_sync",
                    event_type="Sync Failed",
                    severity="error",
                    user_id=account.user_id,
                    worker=self.request.hostname,
                    duration_ms=duration_ms,
                    metadata_payload={"account_id": account_id, "error": str(exc)[:500]}
                )
                
                logger.error("sync_account failed for %s: %s", account_id, type(exc).__name__)
                await db.rollback()
                account.status = "error"
                account.error_message = str(exc)[:500]   # cap length — no full stack in DB
                await db.commit()
                
                # Do not retry on permanent credential or value configuration errors
                if isinstance(exc, ValueError) and any(word in str(exc).lower() for word in ["credential", "token", "decrypt", "provider"]):
                    logger.warning("Permanent config/credential error for %s — skipping retry.", account_id)
                else:
                    raise self.retry(exc=exc)

    finally:
        try:
            lock.release()
        except redis_lib.exceptions.LockNotOwnedError:
            pass  # Lock expired before release — acceptable
