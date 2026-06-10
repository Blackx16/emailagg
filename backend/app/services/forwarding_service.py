import logging
import re
import uuid
import aiosmtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.db.models import MailAccount, Email, ForwardingRule
from app.core.config import settings
from app.core.redis import get_redis

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


async def check_and_forward(email: Email, account: MailAccount, db: AsyncSession) -> bool:
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

                # Send forward email via SMTP
                logger.info(f"Forwarding email {email.id} to {rule.forward_to_email} via rule {rule.id}")
                await _send_forward(email, account, rule.forward_to_email)
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


async def _send_forward(email: Email, account: MailAccount, to_email: str):
    """SMTP delivery for forwarded email using configured SMTP settings."""
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        logger.error("SMTP_HOST or SMTP_USER is not configured in environment settings. Cannot send forward.")
        return

    # Check for OTP to display in forwarding subject/body
    otp = extract_otp(email.subject, email.snippet)
    otp_tag = f" [OTP: {otp}]" if otp else ""

    msg = MIMEMultipart()
    msg["Subject"] = f"Fwd: {email.subject or '(No Subject)'}{otp_tag}"
    msg["From"] = settings.SMTP_FROM_ADDRESS or settings.SMTP_USER
    msg["To"] = to_email
    msg["X-Forwarded-By"] = "EmailAgg"

    header_section = (
        f"---------- Forwarded from {account.email} via EmailAgg ----------\n"
        f"From: {email.from_name or 'Unknown'} <{email.from_email or 'unknown@domain.com'}>\n"
        f"Date: {email.received_at.isoformat() if email.received_at else 'Unknown'}\n"
        f"Subject: {email.subject or '(No Subject)'}\n"
    )
    if otp:
        header_section += f"Extracted OTP Code: {otp}\n"
    header_section += "--------------------------------------------------------\n\n"

    body_content = header_section + (email.snippet or "(No body preview available)")
    msg.attach(MIMEText(body_content, "plain"))

    # Determine encryption parameters from SMTP Port
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
    )
    logger.info(f"Successfully forwarded email to {to_email}")
