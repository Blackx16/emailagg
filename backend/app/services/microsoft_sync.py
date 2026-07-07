import logging
from datetime import datetime, timezone
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import MailAccount, Email, User
from app.services.token_service import get_valid_access_token
from app.workers.notification_tasks import send_telegram_notification

logger = logging.getLogger(__name__)


class MicrosoftSyncService:
    def __init__(self, account: MailAccount, db: AsyncSession):
        self.account = account
        self.db = db

    async def sync(self):
        """Synchronize emails from Microsoft Outlook inbox."""
        logger.info("Starting Microsoft sync for account %s.", str(self.account.id)[-8:])

        # Get valid access token
        access_token = await get_valid_access_token(self.account, self.db)

        url = "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages"
        params = {
            "$top": 50,
            "$select": "id,subject,from,receivedDateTime,bodyPreview,hasAttachments,isRead",
            "$orderby": "receivedDateTime desc",
        }

        # Query messages received since last_sync or creation time
        sync_start_time = self.account.last_sync or self.account.created_at
        if sync_start_time:
            sync_start_utc = sync_start_time if sync_start_time.tzinfo else sync_start_time.replace(tzinfo=timezone.utc)
            sync_start_iso = sync_start_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
            params["$filter"] = f"receivedDateTime ge {sync_start_iso}"

        transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0")
        async with httpx.AsyncClient(transport=transport, timeout=30.0) as client:
            resp = await client.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if resp.status_code != 200:
                raise ValueError(f"Microsoft Graph API call failed: HTTP {resp.status_code}")

            messages_data = resp.json()
            messages = messages_data.get("value", [])

            # Fetch user's telegram ID
            stmt = select(User.telegram_id).where(User.id == self.account.user_id)
            user_result = await self.db.execute(stmt)
            telegram_id = user_result.scalar_one()

            new_emails_count = 0

            existing_msg_ids = set()
            if messages:
                # Bulk fetch existing message IDs to prevent N+1 query problem
                fetched_msg_ids = [msg["id"] for msg in messages]
                stmt_existing = select(Email.message_id).where(
                    Email.mail_account_id == self.account.id,
                    Email.message_id.in_(fetched_msg_ids)
                )
                existing_result = await self.db.execute(stmt_existing)
                existing_msg_ids = set(existing_result.scalars().all())

            # Sync oldest emails first to maintain chronological notification order
            for msg in reversed(messages):
                # Deduplicate by checking if message_id is already stored for this account
                msg_id = msg["id"]
                if msg_id in existing_msg_ids:
                    continue
                
                processed = await self.process_single_message(msg, telegram_id)
                if processed:
                    new_emails_count += 1

            # Update account sync logs
            self.account.last_sync = datetime.now(timezone.utc)
            self.account.status = "active"
            self.account.error_message = None
            await self.db.commit()

            logger.info(f"Microsoft sync finished. Synced {new_emails_count} new emails.")

    async def process_single_message(self, msg: dict, telegram_id: int) -> bool:
        """Process a single incoming email message and dispatch notifications.
        Returns True if processed successfully, False if skipped as duplicate.
        """
        msg_id = msg["id"]
        
        from_data = msg.get("from", {}).get("emailAddress", {})
        from_email = from_data.get("address")
        from_name = from_data.get("name")

        received_str = msg.get("receivedDateTime")
        received_at = None
        if received_str:
            # Clean trailing Z to handle Python datetime conversions
            received_at = datetime.fromisoformat(received_str.replace("Z", "+00:00"))

        # Skip if email was received before the account was connected/created
        if received_at:
            received_at_utc = received_at.astimezone(timezone.utc) if received_at.tzinfo else received_at.replace(tzinfo=timezone.utc)
            created_at_utc = self.account.created_at.astimezone(timezone.utc) if self.account.created_at.tzinfo else self.account.created_at.replace(tzinfo=timezone.utc)
            if received_at_utc < created_at_utc:
                logger.info("Microsoft: Skipping message %s received before account registration (%s < %s)", msg_id, received_at_utc, created_at_utc)
                return False

        # Create Email record
        new_email = Email(
            mail_account_id=self.account.id,
            message_id=msg_id,
            subject=msg.get("subject"),
            from_email=from_email,
            from_name=from_name,
            received_at=received_at,
            snippet=msg.get("bodyPreview"),
            has_attachment=msg.get("hasAttachments", False),
            is_read=msg.get("isRead", False),
            notified=False,
        )

        async with self.db.begin_nested():
            try:
                self.db.add(new_email)
                await self.db.flush()  # Populate new_email.id
            except Exception as e:
                from sqlalchemy.exc import IntegrityError
                if isinstance(e, IntegrityError) or "unique constraint" in str(e).lower():
                    logger.info(f"Duplicate email skipped via unique constraint: {msg_id}")
                    return False
                else:
                    raise e

        # Enqueue Telegram notification task
        from app.services.forwarding_service import extract_otp, check_and_forward
        otp = extract_otp(new_email.subject, new_email.snippet)

        if self.account.notify_telegram:
            notification_payload = {
                "subject": new_email.subject or "(No Subject)",
                "from_name": new_email.from_name or "Unknown",
                "from_email": new_email.from_email or "Unknown",
                "mailbox": self.account.email,
                "email_id": str(new_email.id),
            }
            if otp:
                notification_payload["otp"] = otp
            send_telegram_notification.delay(telegram_id, notification_payload)

        # Check forwarding rules
        await check_and_forward(new_email, self.account, self.db)
        return True
