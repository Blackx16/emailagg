import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import User, MailAccount, ForwardingRule
from app.core.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


class ForwardingRuleSchema(BaseModel):
    id: uuid.UUID
    mail_account_id: uuid.UUID | None
    condition_subject_contains: str | None
    condition_from_domain: str | None
    condition_from_email: str | None
    condition_body_contains: str | None
    forward_to_email: str
    is_active: bool


class ForwardingRuleCreateUpdateSchema(BaseModel):
    mail_account_id: uuid.UUID | None = None
    condition_subject_contains: str | None = None
    condition_from_domain: str | None = None
    condition_from_email: str | None = None
    condition_body_contains: str | None = None
    forward_to_email: EmailStr
    is_active: bool = True


@router.get("", response_model=list[ForwardingRuleSchema])
async def get_user_rules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all forwarding rules for the authenticated user."""
    stmt = select(ForwardingRule).where(ForwardingRule.user_id == current_user.id).order_by(ForwardingRule.created_at.desc())
    result = await db.execute(stmt)
    rules = result.scalars().all()
    return rules


@router.post("", response_model=ForwardingRuleSchema, status_code=status.HTTP_201_CREATED)
async def create_rule(
    payload: ForwardingRuleCreateUpdateSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new forwarding rule for the user."""
    # If mail_account_id is provided, verify it belongs to this user
    if payload.mail_account_id:
        stmt = select(MailAccount).where(
            MailAccount.id == payload.mail_account_id,
            MailAccount.user_id == current_user.id
        )
        res = await db.execute(stmt)
        account = res.scalar_one_or_none()
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mail account not found or access denied."
            )

    new_rule = ForwardingRule(
        user_id=current_user.id,
        mail_account_id=payload.mail_account_id,
        condition_subject_contains=payload.condition_subject_contains.strip() if payload.condition_subject_contains else None,
        condition_from_domain=payload.condition_from_domain.strip().lower() if payload.condition_from_domain else None,
        condition_from_email=payload.condition_from_email.strip().lower() if payload.condition_from_email else None,
        condition_body_contains=payload.condition_body_contains.strip() if payload.condition_body_contains else None,
        forward_to_email=payload.forward_to_email.strip().lower(),
        is_active=payload.is_active
    )

    db.add(new_rule)
    await db.commit()
    await db.refresh(new_rule)

    logger.info(f"User {current_user.id} created forwarding rule {new_rule.id} to {new_rule.forward_to_email}")
    return new_rule


@router.put("/{rule_id}", response_model=ForwardingRuleSchema)
async def update_rule(
    rule_id: uuid.UUID,
    payload: ForwardingRuleCreateUpdateSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an existing forwarding rule."""
    stmt = select(ForwardingRule).where(
        ForwardingRule.id == rule_id,
        ForwardingRule.user_id == current_user.id
    )
    res = await db.execute(stmt)
    rule = res.scalar_one_or_none()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Forwarding rule not found or access denied."
        )

    # If mail_account_id is changing, verify ownership
    if payload.mail_account_id and payload.mail_account_id != rule.mail_account_id:
        stmt_acc = select(MailAccount).where(
            MailAccount.id == payload.mail_account_id,
            MailAccount.user_id == current_user.id
        )
        res_acc = await db.execute(stmt_acc)
        account = res_acc.scalar_one_or_none()
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="New mail account not found or access denied."
            )

    rule.mail_account_id = payload.mail_account_id
    rule.condition_subject_contains = payload.condition_subject_contains.strip() if payload.condition_subject_contains else None
    rule.condition_from_domain = payload.condition_from_domain.strip().lower() if payload.condition_from_domain else None
    rule.condition_from_email = payload.condition_from_email.strip().lower() if payload.condition_from_email else None
    rule.condition_body_contains = payload.condition_body_contains.strip() if payload.condition_body_contains else None
    rule.forward_to_email = payload.forward_to_email.strip().lower()
    rule.is_active = payload.is_active

    await db.commit()
    await db.refresh(rule)

    logger.info(f"User {current_user.id} updated forwarding rule {rule.id}")
    return rule


@router.delete("/{rule_id}")
async def delete_rule(
    rule_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a forwarding rule."""
    stmt = select(ForwardingRule).where(
        ForwardingRule.id == rule_id,
        ForwardingRule.user_id == current_user.id
    )
    res = await db.execute(stmt)
    rule = res.scalar_one_or_none()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Forwarding rule not found or access denied."
        )

    await db.delete(rule)
    await db.commit()

    logger.info(f"User {current_user.id} deleted forwarding rule {rule_id}")
    return {"status": "success", "message": "Rule deleted successfully."}


@router.get("/internal/by-telegram/{telegram_id}")
async def get_rules_by_telegram_id(
    telegram_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Internal endpoint for the Telegram bot to list rules by telegram_id.
    Only accessible from the internal Docker network."""
    stmt_user = select(User).where(User.telegram_id == telegram_id)
    res_user = await db.execute(stmt_user)
    user = res_user.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not registered.")

    stmt = select(ForwardingRule).where(ForwardingRule.user_id == user.id).order_by(ForwardingRule.created_at.desc())
    result = await db.execute(stmt)
    rules = result.scalars().all()

    return [
        {
            "id": str(rule.id),
            "mail_account_id": str(rule.mail_account_id) if rule.mail_account_id else None,
            "condition_subject_contains": rule.condition_subject_contains,
            "condition_from_domain": rule.condition_from_domain,
            "condition_from_email": rule.condition_from_email,
            "condition_body_contains": rule.condition_body_contains,
            "forward_to_email": rule.forward_to_email,
            "is_active": rule.is_active,
        }
        for rule in rules
    ]

