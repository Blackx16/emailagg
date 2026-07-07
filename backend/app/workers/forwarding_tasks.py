import logging
import asyncio
from celery import shared_task
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.db.models import Email, ForwardingRule, MailAccount
from app.workers.sync_tasks import async_to_sync
from app.core.telemetry import telemetry

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="forwarding",
    name="app.workers.forwarding_tasks.forward_email_task",
)
@async_to_sync
async def forward_email_task(self, email_id: str, rule_id: str):
    """
    Deliver a single email to the configured forwarding address via SMTP.
    Runs on the isolated 'forwarding' queue so SMTP failures never block
    sync or notification pipelines.
    """

    async with AsyncSessionLocal() as db:
        # Load email
        email_stmt = select(Email).where(Email.id == email_id)
        email_res = await db.execute(email_stmt)
        email = email_res.scalar_one_or_none()

        if not email:
            logger.warning("forward_email_task: email %s not found — skipping.", email_id)
            return

        # Load rule
        rule_stmt = select(ForwardingRule).where(
            ForwardingRule.id == rule_id,
            ForwardingRule.is_active.is_(True),
        )
        rule_res = await db.execute(rule_stmt)
        rule = rule_res.scalar_one_or_none()

        if not rule:
            logger.warning(
                "forward_email_task: rule %s not found or inactive — skipping.", rule_id
            )
            return

        # Load account
        account_stmt = select(MailAccount).where(MailAccount.id == email.mail_account_id)
        account_res = await db.execute(account_stmt)
        account = account_res.scalar_one_or_none()
        if not account:
            logger.warning("forward_email_task: account for email %s not found — skipping.", email_id)
            return

        try:
            from app.services.forwarding_service import _send_forward
            await _send_forward(email, account, rule.forward_to_email, db)
            logger.info(
                "Forwarded email [%s] via rule [%s] → %s",
                email_id,
                rule_id,
                rule.forward_to_email,
            )
            telemetry.capture(
                str(account.user_id),
                "Email Forwarded",
                {"rule_id": rule_id, "provider": account.provider},
            )
        except Exception as exc:
            logger.error(
                "forward_email_task failed for email %s rule %s: %s",
                email_id,
                rule_id,
                exc,
            )
            raise self.retry(exc=exc)
