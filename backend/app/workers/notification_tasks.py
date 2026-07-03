import logging
import math
import time
import uuid
import html
import httpx
from datetime import datetime, timezone
from celery import shared_task
from sqlalchemy import select
import redis as redis_lib

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.db.models import Notification, Email, MailAccount, User
from app.workers.sync_tasks import async_to_sync
from app.core.telemetry import telemetry

logger = logging.getLogger(__name__)

# Redis client for hourly notification counters
_notif_redis = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)


def _hourly_bucket() -> str:
    """Returns the current UTC hour as an integer string (unix_timestamp // 3600)."""
    return str(int(time.time()) // 3600)


def _check_and_increment_throttle(user_db_id: str, limit: int) -> bool:
    """
    Atomically check and increment the user's hourly notification counter.

    Returns True if the notification should be sent (under limit),
    False if it should be suppressed (at or over limit).

    Redis key: notif_hourly:{user_id}:{hour_bucket}
    TTL: 2 hours (keeps one previous hour for safety)
    """
    key = f"notif_hourly:{user_db_id}:{_hourly_bucket()}"
    pipe = _notif_redis.pipeline()
    pipe.incr(key)
    pipe.expire(key, 7200)  # 2-hour TTL
    results = pipe.execute()
    count = results[0]
    return count <= limit


async def _get_effective_limit(db, user_db_id) -> int:
    """
    Fetch the user's configured limit and compute the effective floor:
        floor = max(5, ceil(active_accounts × 0.1))
        effective = max(user_set, floor)
    """
    stmt_user = select(User).where(User.id == user_db_id)
    res_user = await db.execute(stmt_user)
    user = res_user.scalar_one_or_none()
    if not user:
        return 20  # default fallback

    stmt_acc = select(MailAccount).where(
        MailAccount.user_id == user_db_id,
        MailAccount.status != "disconnected",
    )
    res_acc = await db.execute(stmt_acc)
    active_count = len(res_acc.scalars().all())

    floor = max(5, math.ceil(active_count * 0.1))
    return max(user.notification_limit_per_hour, floor)


async def send_telegram_message(chat_id: int, text: str, reply_markup: dict = None):
    """Call Telegram API to send a message."""
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup

    transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0")
    async with httpx.AsyncClient(transport=transport, timeout=30.0) as client:
        resp = await client.post(url, json=payload)
        if resp.status_code != 200:
            raise ValueError(f"Telegram API error: {resp.status_code}")


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=30,
    rate_limit="1/s",
    queue="notifications",
    name="app.workers.notification_tasks.send_telegram_notification",
)
@async_to_sync
async def send_telegram_notification(self, user_telegram_id: int, email_data: dict):
    """
    Send a Telegram notification for a new email, subject to the user's
    hourly notification limit.  Suppressed notifications are counted silently
    (no error raised) so the worker stays healthy.
    """
    email_id_str = email_data.get("email_id")
    if not email_id_str:
        logger.error("Missing email_id in notification payload.")
        return

    try:
        email_id = uuid.UUID(email_id_str)
    except ValueError:
        logger.error("Invalid email_id format in notification payload.")
        return

    async with AsyncSessionLocal() as db:
        # 1. Resolve user
        stmt_user = select(User).where(User.telegram_id == user_telegram_id)
        res_user = await db.execute(stmt_user)
        user = res_user.scalar_one_or_none()

        if not user:
            logger.error("Notification task: user not found for telegram_id %d.", user_telegram_id)
            return

        user_db_id = user.id

        # 2. Throttle check — before doing any Telegram I/O
        effective_limit = await _get_effective_limit(db, user_db_id)
        allowed = _check_and_increment_throttle(str(user_db_id), effective_limit)

        if not allowed:
            logger.info(
                "Notification suppressed for user %s — hourly limit (%d) reached.",
                user_db_id,
                effective_limit,
            )
            # Mark email as notified so we don't retry it repeatedly
            stmt_email = select(Email).where(Email.id == email_id)
            res_email = await db.execute(stmt_email)
            email_record = res_email.scalar_one_or_none()
            if email_record:
                email_record.notified = True
            await db.commit()
            return

        # 3. Insert pending Notification row
        db_notification = Notification(user_id=user_db_id, email_id=email_id, status="pending")
        db.add(db_notification)
        await db.commit()
        await db.refresh(db_notification)

        # 4. Format message — no raw subject/sender in logs
        subject = email_data.get("subject", "(No Subject)")
        from_name = email_data.get("from_name", "Unknown")
        from_email = email_data.get("from_email", "")
        mailbox = email_data.get("mailbox", "")

        escaped_subject = html.escape(subject)
        escaped_from_name = html.escape(from_name)
        # Only log domain, not full address
        from_domain = from_email.split("@")[-1] if "@" in from_email else "[unknown]"
        escaped_from_email = html.escape(from_email)
        escaped_mailbox = html.escape(mailbox)

        otp = email_data.get("otp")
        otp_prefix = f"🔑 <b>Verification Code:</b> <code>{html.escape(otp)}</code>\n\n" if otp else ""

        text = (
            f"{otp_prefix}📩 <b>New Email Received</b>\n\n"
            f"<b>From:</b> {escaped_from_name} &lt;{escaped_from_email}&gt;\n"
            f"<b>Subject:</b> {escaped_subject}\n"
            f"<b>Mailbox:</b> {escaped_mailbox}\n\n"
            f"<i>Check the web dashboard to read the full message.</i>"
        )

        reply_markup = {
            "inline_keyboard": [
                [{"text": "👁️ Open Dashboard", "web_app": {"url": settings.FRONTEND_URL}}]
            ]
        }

        try:
            # 5. Send
            start_time = time.time()
            await send_telegram_message(user_telegram_id, text, reply_markup)
            duration_ms = int((time.time() - start_time) * 1000)

            # 6. Mark success
            db_notification.status = "sent"
            db_notification.sent_at = datetime.now(timezone.utc)

            stmt_email = select(Email).where(Email.id == email_id)
            res_email = await db.execute(stmt_email)
            email_record = res_email.scalar_one_or_none()
            if email_record:
                email_record.notified = True

            await db.commit()
            logger.info(
                "Telegram notification sent to user (domain: %s) for email %s.",
                from_domain,
                email_id,
            )

            await telemetry.log_event(
                db=db,
                service="worker_notifications",
                event_type="Telegram Notification Sent",
                user_id=user_db_id,
                worker=self.request.hostname,
                duration_ms=duration_ms,
                metadata_payload={"email_id": str(email_id), "domain": from_domain}
            )

        except Exception as exc:
            logger.error(
                "Telegram send failed for user %s: %s", user_db_id, type(exc).__name__
            )
            db_notification.status = "failed"
            db_notification.error_message = str(exc)[:500]
            await db.commit()
            
            await telemetry.log_event(
                db=db,
                service="worker_notifications",
                event_type="Telegram Notification Failed",
                severity="error",
                user_id=user_db_id,
                worker=self.request.hostname,
                metadata_payload={"email_id": str(email_id), "error": str(exc)[:500]}
            )
            
            raise self.retry(exc=exc)
