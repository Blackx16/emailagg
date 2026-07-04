import logging
import re
import uuid
import base64
import httpx
import aiosmtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.db.models import MailAccount, Email, ForwardingRule
from app.core.config import settings
from app.core.redis import get_redis
from app.services.token_service import get_valid_access_token

logger = logging.getLogger(__name__)


def extract_otp(subject: str | None, snippet: str | None) -> str | None:
    """Helper to detect and extract numeric/alphanumeric OTP verification codes."""
    text_to_search = f"{subject or ''} {snippet or ''}"
    
    # Check for keywords indicating a verification request
    keywords = ["code", "otp", "verification", "pin", "passcode", "one-time", "secure", "netflix"]
    if not any(k in text_to_search.lower() for k in keywords):
        return None

    # Pattern 1: Look for exact phrases like "code is 123456" or "OTP: 1234"
    # We require the code to have at least one digit to avoid matching words like "code", "your", etc.
    phrases = [
        r"(?:code|otp|pin|passcode|verification)\s*(?:is\b|:|：)*\s*\b((?=[0-9A-Z]{4,8}\b)[0-9A-Z]*[0-9][0-9A-Z]*)\b",
        r"\b((?=[0-9A-Z]{4,8}\b)[0-9A-Z]*[0-9][0-9A-Z]*)\b\s*(?:is\s*your\s*code|is\s*your\s*verification)",
    ]
    for pattern in phrases:
        match = re.search(pattern, text_to_search, re.IGNORECASE)
        if match:
            return match.group(1)

    # Pattern 2: Fallback to any 4-8 digit number in the text
    digits_match = re.search(r"\b([0-9]{4,8})\b", text_to_search)
    if digits_match:
        return digits_match.group(1)

    return None


async def check_and_forward(
    email: Email,
    account: MailAccount,
    db: AsyncSession,
    original_html: str | None = None,
    original_text: str | None = None,
) -> bool:
    """Check all active rules for this mailbox's user and forward if any match."""
    # Ensure forwarding is enabled on the account
    if not account.forward_enabled:
        return False

    try:
        # Fetch active rules for the user that apply to this account specifically or globally
        stmt = select(ForwardingRule).where(
            ForwardingRule.user_id == account.user_id,
            ForwardingRule.is_active == True,
            or_(
                ForwardingRule.mail_account_id == account.id,
                ForwardingRule.mail_account_id.is_(None)
            )
        )
        result = await db.execute(stmt)
        rules = result.scalars().all()

        if not rules:
            return False

        forwarded_any = False
        for rule in rules:
            if _matches(email, rule):
                # Apply Redis hourly rate limiting (max 50 per user per hour)
                redis = await get_redis()
                hour_key = datetime.now().strftime("%Y%m%d%H")
                redis_key = f"forward_rate:{account.user_id}:{hour_key}"
                
                try:
                    count = await redis.incr(redis_key)
                    if count == 1:
                        await redis.expire(redis_key, 3600)  # 1 hour TTL
                    
                    if count > 50:
                        logger.warning(
                            f"Forward limit exceeded (count={count}) for user {account.user_id}. Skipping rule {rule.id}."
                        )
                        continue
                except Exception as redis_err:
                    logger.error(f"Redis rate limiting check failed: {redis_err}. Proceeding with caution...")

                # Enqueue forward email task
                from app.workers.forwarding_tasks import forward_email_task
                logger.info(f"Enqueueing forward task for email {email.id} to {rule.forward_to_email} via rule {rule.id}")
                forward_email_task.delay(str(email.id), str(rule.id))
                forwarded_any = True

        return forwarded_any

    except Exception as exc:
        # Never let forwarding errors crash the mail sync engine
        logger.error(f"Error in check_and_forward for account {account.email}: {exc}", exc_info=True)
        return False


def _matches(email: Email, rule: ForwardingRule) -> bool:
    """Evaluate forwarding rule conditions using AND logic."""
    if rule.condition_subject_contains:
        subject = email.subject or ""
        if rule.condition_subject_contains.lower() not in subject.lower():
            return False

    if rule.condition_from_domain:
        from_email = (email.from_email or "").lower()
        domain = rule.condition_from_domain.lower().strip().lstrip("@")
        if not (from_email.endswith("@" + domain) or from_email.endswith("." + domain) or from_email == domain):
            return False

    if rule.condition_from_email:
        from_email = (email.from_email or "").lower()
        if from_email != rule.condition_from_email.lower().strip():
            return False

    if rule.condition_body_contains:
        body = email.snippet or ""
        if rule.condition_body_contains.lower() not in body.lower():
            return False

    return True


def extract_gmail_body(msg_detail: dict) -> tuple[str | None, str | None]:
    """Extract HTML and text bodies from Gmail message details recursively."""
    payload = msg_detail.get("payload", {})
    mime_type = payload.get("mimeType")
    body_data = payload.get("body", {}).get("data")

    html_body = None
    text_body = None

    def decode_body(data_str: str) -> str:
        # base64url decode (using standard base64 decoding with - and _ replaced)
        data_str = data_str.replace("-", "+").replace("_", "/")
        padding = len(data_str) % 4
        if padding:
            data_str += "=" * (4 - padding)
        return base64.b64decode(data_str).decode("utf-8", errors="ignore")

    if mime_type == "text/plain" and body_data:
        text_body = decode_body(body_data)
    elif mime_type == "text/html" and body_data:
        html_body = decode_body(body_data)

    def walk_parts(parts_list):
        nonlocal html_body, text_body
        for part in parts_list:
            part_mime = part.get("mimeType")
            part_body = part.get("body", {}).get("data")

            if part_mime == "text/plain" and part_body and not text_body:
                text_body = decode_body(part_body)
            elif part_mime == "text/html" and part_body and not html_body:
                html_body = decode_body(part_body)

            subparts = part.get("parts")
            if subparts:
                walk_parts(subparts)

    parts = payload.get("parts")
    if parts:
        walk_parts(parts)

    return html_body, text_body


async def _send_forward(
    email: Email,
    account: MailAccount,
    to_email: str,
    db: AsyncSession,
    original_html: str | None = None,
    original_text: str | None = None,
):
    """Deliver forwarded email using Google/Microsoft APIs for OAuth accounts or SMTP fallback."""
    # Check for OTP to display in forwarding subject/body
    otp = extract_otp(email.subject, email.snippet)
    otp_tag = f" [OTP: {otp}]" if otp else ""
    subject = f"Fwd: {email.subject or '(No Subject)'}{otp_tag}"

    html_body = original_html
    text_body = original_text

    # On-demand fetching for OAuth accounts if not already provided (e.g. from IMAP sync)
    if not html_body and not text_body:
        if account.provider == "google":
            try:
                access_token = await get_valid_access_token(account, db)
                url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{email.message_id}?format=full"
                transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0")
                async with httpx.AsyncClient(transport=transport, timeout=10.0) as client:
                    resp = await client.get(url, headers={"Authorization": f"Bearer {access_token}"})
                    if resp.status_code == 200:
                        gmail_detail = resp.json()
                        html_body, text_body = extract_gmail_body(gmail_detail)
                    else:
                        logger.error(f"Failed to fetch full Gmail message for on-demand forwarding: {resp.status_code}")
            except Exception as e:
                logger.error(f"Error fetching Gmail details on-demand: {e}", exc_info=True)

        elif account.provider == "microsoft":
            try:
                access_token = await get_valid_access_token(account, db)
                url = f"https://graph.microsoft.com/v1.0/me/messages/{email.message_id}?$select=body"
                transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0")
                async with httpx.AsyncClient(transport=transport, timeout=10.0) as client:
                    resp = await client.get(url, headers={"Authorization": f"Bearer {access_token}"})
                    if resp.status_code == 200:
                        body_info = resp.json().get("body", {})
                        if body_info.get("contentType") == "html":
                            html_body = body_info.get("content")
                        else:
                            text_body = body_info.get("content")
                    else:
                        logger.error(f"Failed to fetch full Microsoft message for on-demand forwarding: {resp.status_code}")
            except Exception as e:
                logger.error(f"Error fetching Microsoft details on-demand: {e}", exc_info=True)

    # 1. Build Text version of forwarding headers and body
    text_header = (
        f"---------- Forwarded from {account.email} via EmailAgg ----------\n"
        f"From: {email.from_name or 'Unknown'} <{email.from_email or 'unknown@domain.com'}>\n"
        f"Date: {email.received_at.isoformat() if email.received_at else 'Unknown'}\n"
        f"Subject: {email.subject or '(No Subject)'}\n"
    )
    if otp:
        text_header += f"Extracted OTP Code: {otp}\n"
    text_header += "--------------------------------------------------------\n\n"
    text_content = text_header + (text_body or email.snippet or "(No body preview available)")

    # 2. Build HTML version of forwarding headers and body (if HTML body is available)
    html_content = None
    if html_body:
        html_header = (
            f"<div style='font-family: Arial, sans-serif; font-size: 14px; color: #333; "
            f"border-left: 3px solid #ccc; padding-left: 10px; margin-bottom: 20px; line-height: 1.5;'>"
            f"<b>---------- Forwarded from {account.email} via EmailAgg ----------</b><br>"
            f"<b>From:</b> {email.from_name or 'Unknown'} &lt;{email.from_email or 'unknown@domain.com'}&gt;<br>"
            f"<b>Date:</b> {email.received_at.isoformat() if email.received_at else 'Unknown'}<br>"
            f"<b>Subject:</b> {email.subject or '(No Subject)'}<br>"
        )
        if otp:
            html_header += f"<b>Extracted OTP Code:</b> <span style='font-size: 16px; font-weight: bold; color: #d93025;'>{otp}</span><br>"
        html_header += "</div><br>"
        html_content = html_header + html_body

    if account.provider == "google":
        logger.info(f"Forwarding via Gmail API from {account.email}")
        access_token = await get_valid_access_token(account, db)
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = account.email
        msg["To"] = to_email
        msg["X-Forwarded-By"] = "EmailAgg"
        
        # Always attach text first, then HTML
        msg.attach(MIMEText(text_content, "plain"))
        if html_content:
            msg.attach(MIMEText(html_content, "html"))

        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
        transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0")
        async with httpx.AsyncClient(transport=transport, timeout=10.0) as client:
            resp = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={"raw": raw_message},
            )
            if resp.status_code != 200:
                raise ValueError(f"Gmail API forwarding failed: HTTP {resp.status_code} - {resp.text}")
        logger.info(f"Successfully forwarded email via Gmail API to {to_email}")

    elif account.provider == "microsoft":
        logger.info(f"Forwarding via Microsoft Graph API from {account.email}")
        access_token = await get_valid_access_token(account, db)

        payload = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML" if html_content else "Text",
                    "content": html_content if html_content else text_content
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": to_email
                        }
                    }
                ]
            },
            "saveToSentItems": False
        }
        url = "https://graph.microsoft.com/v1.0/me/sendMail"
        transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0")
        async with httpx.AsyncClient(transport=transport, timeout=10.0) as client:
            resp = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if resp.status_code != 202:
                raise ValueError(f"Microsoft Graph API forwarding failed: HTTP {resp.status_code} - {resp.text}")
        logger.info(f"Successfully forwarded email via Microsoft Graph API to {to_email}")

    else:
        # Fallback to SMTP for custom IMAP mailboxes
        if not settings.SMTP_HOST or not settings.SMTP_USER:
            raise ValueError("SMTP_HOST or SMTP_USER is not configured in environment settings. Cannot send SMTP forward.")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM_ADDRESS or settings.SMTP_USER
        msg["To"] = to_email
        msg["X-Forwarded-By"] = "EmailAgg"
        
        msg.attach(MIMEText(text_content, "plain"))
        if html_content:
            msg.attach(MIMEText(html_content, "html"))

        use_tls = (settings.SMTP_PORT == 465)
        start_tls = (settings.SMTP_PORT == 587)

        logger.debug(f"Sending SMTP email via {settings.SMTP_HOST}:{settings.SMTP_PORT} (TLS={use_tls}, StartTLS={start_tls})")
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            use_tls=use_tls,
            start_tls=start_tls,
            timeout=10.0,
        )
        logger.info(f"Successfully forwarded email via SMTP to {to_email}")
