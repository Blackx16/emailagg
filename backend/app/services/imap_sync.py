import logging
from datetime import datetime, timezone
import aioimaplib
import email
from email.utils import parseaddr, parsedate_to_datetime
from email.header import decode_header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import MailAccount, Email, User
from app.core.encryption import decrypt_token
from app.workers.notification_tasks import send_telegram_notification

logger = logging.getLogger(__name__)


class IMAPSyncService:
    def __init__(self, account: MailAccount, db: AsyncSession):
        self.account = account
        self.db = db

    async def sync(self):
        """Synchronize emails from custom IMAP mailbox."""
        logger.info(f"Starting IMAP sync for {self.account.email}")

        # Decrypt app password
        password = decrypt_token(self.account.access_token_encrypted)

        # Establish SSL connection
        imap_client = aioimaplib.IMAP4_SSL(
            host=self.account.imap_host, port=self.account.imap_port or 993
        )
        await imap_client.wait_hello_from_server()

        try:
            # Login
            login_resp = await imap_client.login(self.account.email, password)
            if login_resp.result != "OK":
                raise ValueError(f"IMAP login failed: {login_resp.result}")

            # Select Inbox folder
            select_resp = await imap_client.select("INBOX")
            if select_resp.result != "OK":
                raise ValueError(f"IMAP select INBOX failed: {select_resp.result}")

            # Define search criteria (UID-based)
            if self.account.last_sync:
                # IMAP SINCE expects DD-Mon-YYYY format (e.g. 04-Jun-2026)
                since_date = self.account.last_sync.strftime("%d-%b-%Y")
                search_resp = await imap_client.uid("search", f"SINCE {since_date}")
            else:
                search_resp = await imap_client.uid("search", "ALL")

            if search_resp.result != "OK":
                raise ValueError(f"IMAP search failed: {search_resp.result}")

            # Parse UIDs from response
            search_line = search_resp.lines[0]
            if search_line.startswith(b"* SEARCH"):
                search_line = search_line[9:]
            elif search_line.startswith(b"*"):
                parts = search_line.split()
                if len(parts) > 1 and parts[1] == b"SEARCH":
                    search_line = b" ".join(parts[2:])

            uids = search_line.split()
            # Limit to latest 50 for local performance constraints
            uids = uids[-50:]

            # Fetch user's telegram ID
            stmt = select(User.telegram_id).where(User.id == self.account.user_id)
            user_result = await self.db.execute(stmt)
            telegram_id = user_result.scalar_one()

            new_emails_count = 0
            # Sync oldest emails first to maintain chronological notification order
            for uid_bytes in uids:
                uid = uid_bytes.decode()

                # 1. Fetch headers first to retrieve Message-ID for deduplication
                header_resp = await imap_client.uid(
                    "fetch", uid, "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])"
                )
                if header_resp.result != "OK":
                    logger.error(f"Failed to fetch IMAP headers for UID {uid}")
                    continue

                raw_header = None
                for line in header_resp.lines:
                    if not line.startswith(b"*") and line != b")" and len(line) > 0:
                        raw_header = line
                        break

                message_id = None
                if raw_header:
                    header_msg = email.message_from_bytes(raw_header)
                    message_id = header_msg.get("Message-ID")

                # Fallback unique identifier if Message-ID is missing
                if not message_id:
                    message_id = f"imap-uid-{uid}"
                else:
                    message_id = message_id.strip()

                # Deduplicate by checking if message_id is already stored for this account
                stmt_email = select(Email).where(
                    Email.mail_account_id == self.account.id, Email.message_id == message_id
                )
                email_result = await self.db.execute(stmt_email)
                existing_email = email_result.scalar_one_or_none()

                if existing_email:
                    continue

                # 2. Fetch full raw email bytes (use PEEK to avoid marking it read)
                fetch_resp = await imap_client.uid("fetch", uid, "BODY.PEEK[]")
                if fetch_resp.result != "OK":
                    logger.error(f"Failed to fetch full IMAP email for UID {uid}")
                    continue

                raw_email = None
                for line in fetch_resp.lines:
                    if not line.startswith(b"*") and line != b")" and len(line) > 0:
                        raw_email = line
                        break

                if not raw_email:
                    logger.error(f"Empty raw email content for UID {uid}")
                    continue

                # Parse the raw MIME email
                msg = email.message_from_bytes(raw_email)

                subject = self._decode_header_value(msg.get("Subject", ""))
                from_header = msg.get("From", "")
                from_name, from_email = parseaddr(from_header)

                received_at = None
                date_header = msg.get("Date")
                if date_header:
                    try:
                        received_at = parsedate_to_datetime(date_header)
                    except Exception:
                        pass
                if not received_at:
                    received_at = datetime.now(timezone.utc)

                snippet = self._get_email_snippet(msg)
                has_attachment = self._check_attachments(msg)

                # Create Email record
                new_email = Email(
                    mail_account_id=self.account.id,
                    message_id=message_id,
                    subject=subject,
                    from_email=from_email or None,
                    from_name=from_name or None,
                    received_at=received_at,
                    snippet=snippet,
                    has_attachment=has_attachment,
                    is_read=False,  # Read sync is provider-specific; defaults to False
                    notified=False,
                )

                async with self.db.begin_nested():
                    try:
                        self.db.add(new_email)
                        await self.db.flush()  # Populate new_email.id
                    except Exception as e:
                        from sqlalchemy.exc import IntegrityError
                        if isinstance(e, IntegrityError) or "unique constraint" in str(e).lower():
                            logger.info(f"Duplicate email skipped via unique constraint: {message_id}")
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

            # Update account sync logs
            self.account.last_sync = datetime.now(timezone.utc)
            self.account.status = "active"
            self.account.error_message = None
            await self.db.commit()

            logger.info(f"IMAP sync finished. Synced {new_emails_count} new emails.")

        finally:
            try:
                await imap_client.logout()
            except Exception:
                pass

    def _decode_header_value(self, value: str) -> str:
        if not value:
            return ""
        decoded_parts = decode_header(value)
        decoded_str = ""
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                decoded_str += part.decode(encoding or "utf-8", errors="ignore")
            else:
                decoded_str += part
        return decoded_str

    def _get_email_snippet(self, msg) -> str:
        snippet = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    payload = part.get_payload(decode=True)
                    if payload:
                        snippet = payload.decode("utf-8", errors="ignore")
                        break
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                snippet = payload.decode("utf-8", errors="ignore")
        return snippet[:500].strip()

    def _check_attachments(self, msg) -> bool:
        if msg.is_multipart():
            for part in msg.walk():
                content_disposition = str(part.get("Content-Disposition"))
                if "attachment" in content_disposition:
                    return True
        return False
