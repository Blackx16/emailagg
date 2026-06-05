import logging
from datetime import datetime, timezone
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import MailAccount, Email, User
from app.services.token_service import get_valid_access_token
from app.workers.notification_tasks import send_telegram_notification

logger = logging.getLogger(__name__)


class GmailSyncService:
    def __init__(self, account: MailAccount, db: AsyncSession):
        self.account = account
        self.db = db

    async def sync(self):
        """Synchronize emails from Google Gmail inbox."""
        logger.info(f"Starting Gmail sync for {self.account.email}")

        # Get valid access token
        access_token = await get_valid_access_token(self.account, self.db)

        # 1. Fetch latest 50 message summaries from inbox
        list_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
        params = {"maxResults": 50, "q": "label:INBOX"}

        # Google's after filter accepts Unix timestamps
        if self.account.last_sync:
            after_timestamp = int(self.account.last_sync.replace(tzinfo=timezone.utc).timestamp())
            params["q"] += f" after:{after_timestamp}"

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            resp = await client.get(list_url, params=params, headers=headers)

            if resp.status_code != 200:
                raise ValueError(f"Gmail messages list failed: {resp.text}")

            list_data = resp.json()
            messages = list_data.get("messages", [])

            # Fetch user's telegram ID
            stmt = select(User.telegram_id).where(User.id == self.account.user_id)
            user_result = await self.db.execute(stmt)
            telegram_id = user_result.scalar_one()

            new_emails_count = 0
            # Sync oldest emails first to maintain chronological notification order
            for msg_summary in reversed(messages):
                msg_id = msg_summary["id"]

                # Deduplicate by checking if message_id is already stored for this account
                stmt_email = select(Email).where(
                    Email.mail_account_id == self.account.id, Email.message_id == msg_id
                )
                email_result = await self.db.execute(stmt_email)
                existing_email = email_result.scalar_one_or_none()

                if existing_email:
                    continue

                # Fetch metadata headers for this message (efficient retrieval)
                detail_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}"
                detail_params = {
                    "format": "metadata",
                    "metadataHeaders": ["Subject", "From", "Date"],
                }

                detail_resp = await client.get(detail_url, params=detail_params, headers=headers)
                if detail_resp.status_code != 200:
                    logger.error(
                        f"Failed to fetch Gmail message details for {msg_id}: {detail_resp.text}"
                    )
                    continue

                msg_detail = detail_resp.json()
                headers_list = msg_detail.get("payload", {}).get("headers", [])

                subject = next((h["value"] for h in headers_list if h["name"].lower() == "subject"), "")
                from_header = next((h["value"] for h in headers_list if h["name"].lower() == "from"), "")
                date_header = next((h["value"] for h in headers_list if h["name"].lower() == "date"), "")

                from_name, from_email = self._parse_from_header(from_header)
                received_at = self._parse_date_header(date_header)

                # Create Email record
                new_email = Email(
                    mail_account_id=self.account.id,
                    message_id=msg_id,
                    subject=subject,
                    from_email=from_email,
                    from_name=from_name,
                    received_at=received_at,
                    snippet=msg_detail.get("snippet"),
                    has_attachment=self._has_attachments(msg_detail),
                    is_read="UNREAD" not in msg_detail.get("labelIds", []),
                    notified=False,
                )
                self.db.add(new_email)
                await self.db.flush()  # Populate new_email.id

                # Enqueue Telegram notification task
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

            logger.info(f"Gmail sync finished. Synced {new_emails_count} new emails.")

    def _parse_from_header(self, from_header: str) -> tuple[str, str]:
        from email.utils import parseaddr

        name, addr = parseaddr(from_header)
        return name or None, addr or None

    def _parse_date_header(self, date_header: str) -> datetime:
        from email.utils import parsedate_to_datetime

        try:
            return parsedate_to_datetime(date_header)
        except Exception:
            return datetime.now(timezone.utc)

    def _has_attachments(self, msg_detail: dict) -> bool:
        payload = msg_detail.get("payload", {})
        parts = payload.get("parts", [])

        def walk_parts(parts_list):
            for part in parts_list:
                filename = part.get("filename")
                body = part.get("body", {})
                attachment_id = body.get("attachmentId")
                if filename or attachment_id:
                    return True
                subparts = part.get("parts", [])
                if subparts and walk_parts(subparts):
                    return True
            return False

        return walk_parts(parts)
