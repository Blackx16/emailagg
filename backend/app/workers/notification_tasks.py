import logging
import uuid
import html
import httpx
from datetime import datetime, timezone
from celery import shared_task
from sqlalchemy import select

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.db.models import Notification, Email, User
from app.workers.sync_tasks import async_to_sync

logger = logging.getLogger(__name__)


async def send_telegram_message(chat_id: int, text: str, reply_markup: dict = None):
    """Call Telegram API to send message."""
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload)
        if resp.status_code != 200:
            raise ValueError(f"Telegram API response error: {resp.text}")


@shared_task(bind=True, max_retries=5, default_retry_delay=30, rate_limit="1/s")
@async_to_sync
async def send_telegram_notification(self, user_telegram_id: int, email_data: dict):
    """
    Send a Telegram notification for a new email, and record it in the notifications audit log.
    """
    email_id_str = email_data.get("email_id")
    if not email_id_str:
        logger.error("Missing email_id in notification payload.")
        return

    try:
        email_id = uuid.UUID(email_id_str)
    except ValueError:
        logger.error(f"Invalid email_id format: {email_id_str}")
        return

    async with AsyncSessionLocal() as db:
        # 1. Fetch user ID inside the database
        stmt_user = select(User.id).where(User.telegram_id == user_telegram_id)
        res_user = await db.execute(stmt_user)
        user_db_id = res_user.scalar_one_or_none()

        if not user_db_id:
            logger.error(f"User with telegram_id {user_telegram_id} not found in database.")
            return

        # 2. Insert pending Notification row in database
        db_notification = Notification(user_id=user_db_id, email_id=email_id, status="pending")
        db.add(db_notification)
        await db.commit()
        await db.refresh(db_notification)

        # 3. Format message and inline keyboard
        subject = email_data.get("subject", "(No Subject)")
        from_name = email_data.get("from_name", "Unknown")
        from_email = email_data.get("from_email", "Unknown")
        mailbox = email_data.get("mailbox", "")

        # Escape HTML characters to prevent parsing errors in Telegram API
        escaped_subject = html.escape(subject)
        escaped_from_name = html.escape(from_name)
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
            # 4. Call Telegram API
            await send_telegram_message(user_telegram_id, text, reply_markup)

            # 5. Update notification and email states on success
            db_notification.status = "sent"
            db_notification.sent_at = datetime.now(timezone.utc)

            stmt_email = select(Email).where(Email.id == email_id)
            res_email = await db.execute(stmt_email)
            email_record = res_email.scalar_one_or_none()
            if email_record:
                email_record.notified = True

            await db.commit()
            logger.info(
                f"Telegram notification sent successfully to {user_telegram_id} for email {email_id}."
            )

        except Exception as exc:
            logger.error(f"Telegram alert call failed for user {user_telegram_id}: {exc}")

            # Update database status to failed
            db_notification.status = "failed"
            db_notification.error_message = str(exc)
            await db.commit()

            # Retry task
            raise self.retry(exc=exc)
