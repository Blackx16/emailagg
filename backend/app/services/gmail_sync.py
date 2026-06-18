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
        """Synchronize emails from Google Gmail inbox.

        Uses Gmail History API for incremental sync when a historyId is stored,
        falling back to messages.list for the initial sync or when history expires.
        """
        logger.info("Starting Gmail sync for account %s.", str(self.account.id)[-8:])

        # Get valid access token
        access_token = await get_valid_access_token(self.account, self.db)

        # Fetch user's telegram ID (needed for notifications)
        stmt = select(User.telegram_id).where(User.id == self.account.user_id)
        user_result = await self.db.execute(stmt)
        telegram_id = user_result.scalar_one()

        transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0")
        async with httpx.AsyncClient(transport=transport, timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {access_token}"}

            if self.account.history_id:
                # Incremental sync via History API
                new_count = await self._sync_via_history(client, headers, telegram_id)
            else:
                # Initial full sync via messages.list
                new_count = await self._sync_via_messages_list(client, headers, telegram_id)

            # Update account sync status
            self.account.last_sync = datetime.now(timezone.utc)
            self.account.status = "active"
            self.account.error_message = None
            await self.db.commit()

            logger.info("Gmail sync finished for account %s. Synced %d new emails.", str(self.account.id)[-8:], new_count)

    async def _sync_via_history(
        self, client: httpx.AsyncClient, headers: dict, telegram_id: int
    ) -> int:
        """Incremental sync using Gmail History API — only fetches changes since last historyId."""
        history_url = "https://gmail.googleapis.com/gmail/v1/users/me/history"
        params = {
            "startHistoryId": self.account.history_id,
            "historyTypes": "messageAdded",
            "labelId": "INBOX",
        }

        resp = await client.get(history_url, params=params, headers=headers)

        if resp.status_code == 404:
            # historyId expired (Gmail only keeps ~30 days). Fall back to full sync.
            logger.warning(
                "Gmail historyId expired for account %s, falling back to full sync.",
                str(self.account.id)[-8:],
            )
            self.account.history_id = None
            return await self._sync_via_messages_list(client, headers, telegram_id)

        if resp.status_code != 200:
            raise ValueError(f"Gmail history.list failed: HTTP {resp.status_code}")

        history_data = resp.json()

        # Update historyId for next sync
        new_history_id = history_data.get("historyId")
        if new_history_id:
            self.account.history_id = str(new_history_id)

        # Extract new message IDs from history records
        new_msg_ids = set()
        for record in history_data.get("history", []):
            for msg_added in record.get("messagesAdded", []):
                msg = msg_added.get("message", {})
                # Only include INBOX messages
                label_ids = msg.get("labelIds", [])
                if "INBOX" in label_ids:
                    new_msg_ids.add(msg["id"])

        if not new_msg_ids:
            return 0

        # Fetch and store new messages
        return await self._fetch_and_store_messages(
            client, headers, telegram_id, list(new_msg_ids)
        )

    async def _sync_via_messages_list(
        self, client: httpx.AsyncClient, headers: dict, telegram_id: int
    ) -> int:
        """Initial full sync using messages.list — fetches latest inbox messages."""
        list_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
        params = {"maxResults": 50, "q": "label:INBOX"}

        # Only fetch messages after last sync time or creation time
        sync_start_time = self.account.last_sync or self.account.created_at
        if sync_start_time:
            sync_start_utc = sync_start_time if sync_start_time.tzinfo else sync_start_time.replace(tzinfo=timezone.utc)
            after_timestamp = int(sync_start_utc.timestamp())
            params["q"] += f" after:{after_timestamp}"

        resp = await client.get(list_url, params=params, headers=headers)
        if resp.status_code != 200:
            raise ValueError(f"Gmail messages.list failed: HTTP {resp.status_code}")

        list_data = resp.json()
        messages = list_data.get("messages", [])

        # Store the historyId from the profile for future incremental syncs
        profile_resp = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/profile", headers=headers
        )
        if profile_resp.status_code == 200:
            profile_data = profile_resp.json()
            history_id = profile_data.get("historyId")
            if history_id:
                self.account.history_id = str(history_id)

        if not messages:
            return 0

        msg_ids = [m["id"] for m in reversed(messages)]  # oldest first
        return await self._fetch_and_store_messages(client, headers, telegram_id, msg_ids)

    async def _fetch_and_store_messages(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        telegram_id: int,
        msg_ids: list[str],
    ) -> int:
        """Fetch message details and store new emails, deduplicating by message_id."""
        new_emails_count = 0

        for msg_id in msg_ids:
            # Deduplicate by checking if message_id is already stored for this account
            stmt_email = select(Email).where(
                Email.mail_account_id == self.account.id, Email.message_id == msg_id
            )
            email_result = await self.db.execute(stmt_email)
            existing_email = email_result.scalar_one_or_none()

            if existing_email:
                continue

            # Fetch metadata headers for this message (efficient retrieval)
            detail_url = (
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}"
            )
            detail_params = {
                "format": "metadata",
                "metadataHeaders": ["Subject", "From", "Date"],
            }

            detail_resp = await client.get(
                detail_url, params=detail_params, headers=headers
            )
            if detail_resp.status_code != 200:
                logger.error(
                    "Failed to fetch Gmail message details for msg_id %s: HTTP %d",
                    msg_id,
                    detail_resp.status_code,
                )
                continue

            msg_detail = detail_resp.json()
            headers_list = msg_detail.get("payload", {}).get("headers", [])

            subject = next(
                (h["value"] for h in headers_list if h["name"].lower() == "subject"), ""
            )
            from_header = next(
                (h["value"] for h in headers_list if h["name"].lower() == "from"), ""
            )
            date_header = next(
                (h["value"] for h in headers_list if h["name"].lower() == "date"), ""
            )

            from_name, from_email = self._parse_from_header(from_header)
            received_at = self._parse_date_header(date_header)

            # Skip if email was received before the account was connected/created
            if received_at:
                received_at_utc = received_at.astimezone(timezone.utc) if received_at.tzinfo else received_at.replace(tzinfo=timezone.utc)
                created_at_utc = self.account.created_at.astimezone(timezone.utc) if self.account.created_at.tzinfo else self.account.created_at.replace(tzinfo=timezone.utc)
                if received_at_utc < created_at_utc:
                    logger.info("Gmail: Skipping message %s received before account registration (%s < %s)", msg_id, received_at_utc, created_at_utc)
                    continue

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

            async with self.db.begin_nested():
                try:
                    self.db.add(new_email)
                    await self.db.flush()  # Populate new_email.id
                except Exception as e:
                    from sqlalchemy.exc import IntegrityError
                    if isinstance(e, IntegrityError) or "unique constraint" in str(e).lower():
                        logger.debug("Duplicate email skipped (msg_id already stored).")
                        continue
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
            new_emails_count += 1

        return new_emails_count

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
