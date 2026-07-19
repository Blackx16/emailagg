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
        logger.info("Starting IMAP sync for account %s.", str(self.account.id)[-8:])

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
            sync_start_time = self.account.last_sync or self.account.created_at
            if sync_start_time:
                # IMAP SINCE expects DD-Mon-YYYY format (e.g. 04-Jun-2026)
                sync_start_utc = sync_start_time if sync_start_time.tzinfo else sync_start_time.replace(tzinfo=timezone.utc)
                since_date = sync_start_utc.strftime("%d-%b-%Y")
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

            # 1. First pass: Fetch headers to retrieve Message-ID for bounded deduplication
            uid_to_msg_id = {}
            for uid_bytes in uids:
                uid = uid_bytes.decode()
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

                uid_to_msg_id[uid] = message_id

            # Chunked bounded query to avoid O(N) memory leak
            msg_ids_to_check = list(uid_to_msg_id.values())
            existing_message_ids = set()
            chunk_size = 100
            for i in range(0, len(msg_ids_to_check), chunk_size):
                chunk = msg_ids_to_check[i:i + chunk_size]
                if chunk:
                    stmt_existing = select(Email.message_id).where(
                        Email.mail_account_id == self.account.id,
                        Email.message_id.in_(chunk)
                    )
                    existing_result = await self.db.execute(stmt_existing)
                    existing_message_ids.update(existing_result.scalars().all())

            # Sync oldest emails first to maintain chronological notification order
            for uid_bytes in uids:
                uid = uid_bytes.decode()

                if uid not in uid_to_msg_id:
                    continue

                message_id = uid_to_msg_id[uid]

                # Deduplicate using the bounded existing message IDs
                if message_id in existing_message_ids:
                    continue

                # Add it to the set to prevent in-batch duplicates
                existing_message_ids.add(message_id)

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

                # Skip if email was received before the account was connected/created
                received_at_utc = received_at.astimezone(timezone.utc) if received_at.tzinfo else received_at.replace(tzinfo=timezone.utc)
                created_at_utc = self.account.created_at.astimezone(timezone.utc) if self.account.created_at.tzinfo else self.account.created_at.replace(tzinfo=timezone.utc)
                if received_at_utc < created_at_utc:
                    logger.info("IMAP: Skipping message %s received before account registration (%s < %s)", message_id, received_at_utc, created_at_utc)
                    continue

                snippet = self._get_email_snippet(msg)
                has_attachment = self._check_attachments(msg)

                # Create Email record
                html_body_store, text_body_store = self._get_email_bodies(msg)
                new_email = Email(
                    mail_account_id=self.account.id,
                    message_id=message_id,
                    subject=subject,
                    from_email=from_email or None,
                    from_name=from_name or None,
                    received_at=received_at,
                    snippet=snippet,
                    body_html=html_body_store,
                    body_text=text_body_store,
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

                # Extract HTML/text bodies for forwarding
                html_body, text_body = self._get_email_bodies(msg)

                # Check forwarding rules
                await check_and_forward(
                    new_email,
                    self.account,
                    self.db,
                    original_html=html_body,
                    original_text=text_body,
                )
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

    def _get_email_bodies(self, msg) -> tuple[str | None, str | None]:
        html_body = None
        text_body = None
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                if "attachment" not in content_disposition:
                    if content_type == "text/plain" and not text_body:
                        payload = part.get_payload(decode=True)
                        if payload:
                            text_body = payload.decode("utf-8", errors="ignore")
                    elif content_type == "text/html" and not html_body:
                        payload = part.get_payload(decode=True)
                        if payload:
                            html_body = payload.decode("utf-8", errors="ignore")
        else:
            content_type = msg.get_content_type()
            payload = msg.get_payload(decode=True)
            if payload:
                val = payload.decode("utf-8", errors="ignore")
                if content_type == "text/html":
                    html_body = val
                else:
                    text_body = val
        return html_body, text_body
