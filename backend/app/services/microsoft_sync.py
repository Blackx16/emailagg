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
        logger.info(f"Starting Microsoft sync for {self.account.email}")

        # Get valid access token
        access_token = await get_valid_access_token(self.account, self.db)

        url = "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages"
        params = {
            "$top": 50,
            "$select": "id,subject,from,receivedDateTime,bodyPreview,hasAttachments,isRead",
            "$orderby": "receivedDateTime desc",
        }

        # Query messages received since last_sync
        if self.account.last_sync:
            last_sync_iso = (
                self.account.last_sync.replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            )
            params["$filter"] = f"receivedDateTime ge {last_sync_iso}"

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if resp.status_code != 200:
                raise ValueError(f"Microsoft Graph API call failed: {resp.text}")

            messages_data = resp.json()
            messages = messages_data.get("value", [])

            # Fetch user's telegram ID
            stmt = select(User.telegram_id).where(User.id == self.account.user_id)
            user_result = await self.db.execute(stmt)
            telegram_id = user_result.scalar_one()

            new_emails_count = 0
            # Sync oldest emails first to maintain chronological notification order
            for msg in reversed(messages):
                msg_id = msg["id"]

                # Deduplicate by checking if message_id is already stored for this account
                stmt_email = select(Email).where(
                    Email.mail_account_id == self.account.id, Email.message_id == msg_id
                )
                email_result = await self.db.execute(stmt_email)
                existing_email = email_result.scalar_one_or_none()

                if existing_email:
                    continue

                from_data = msg.get("from", {}).get("emailAddress", {})
                from_email = from_data.get("address")
                from_name = from_data.get("name")

                received_str = msg.get("receivedDateTime")
                received_at = None
                if received_str:
                    # Clean trailing Z to handle Python datetime conversions
                    received_at = datetime.fromisoformat(received_str.replace("Z", "+00:00"))

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
                            continue
                        else:
                            raise e

                # Enqueue Telegram notification task
                if self.account.notify_telegram:
                    notification_payload = {
                        "subject": new_email.subject or "(No Subject)",
                        "from_name": new_email.from_name or "Unknown",
                        "from_email": new_email.from_email or "Unknown",
                        "mailbox": self.account.email,
                        "email_id": str(new_email.id),
                    }
                    send_telegram_notification.delay(telegram_id, notification_payload)
                new_emails_count += 1

            # Update account sync logs
            self.account.last_sync = datetime.now(timezone.utc)
            self.account.status = "active"
            self.account.error_message = None
            await self.db.commit()

            logger.info(f"Microsoft sync finished. Synced {new_emails_count} new emails.")
