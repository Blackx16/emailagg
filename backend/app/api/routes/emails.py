import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import User, MailAccount, Email
from app.core.security import get_current_user
from app.services.email_service import get_paginated_emails

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("")
async def get_emails(
    account_id: str | None = Query(None),
    provider: str | None = Query(None),
    is_read: bool | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve paginated aggregated emails for the logged-in user.
    Optionally filter by a specific mail_account_id, provider, read status, and search query.
    """
    return await get_paginated_emails(
        db=db,
        current_user=current_user,
        account_id=account_id,
        provider=provider,
        is_read=is_read,
        search=search,
        page=page,
        limit=limit
    )

@router.get("/{email_id}")
async def get_email_details(
    email_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve single email details. Validates that the email belongs 
    to a mailbox owned by the logged-in user.
    """
    try:
        email_uuid = uuid.UUID(email_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email_id UUID format."
        )
        
    stmt = select(Email).join(MailAccount).where(
        Email.id == email_uuid,
        MailAccount.user_id == current_user.id,
        MailAccount.deliver_to_dashboard == True
    )
    res = await db.execute(stmt)
    email = res.scalar_one_or_none()
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found or access denied."
        )
        
    return {
        "id": str(email.id),
        "mail_account_id": str(email.mail_account_id),
        "message_id": email.message_id,
        "subject": email.subject,
        "from_email": email.from_email,
        "from_name": email.from_name,
        "received_at": email.received_at.isoformat() if email.received_at else None,
        "snippet": email.snippet,
        "has_attachment": email.has_attachment,
        "is_read": email.is_read,
        "created_at": email.created_at.isoformat() if email.created_at else None
    }
