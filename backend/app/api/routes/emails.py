import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.db.models import User, MailAccount, Email
from app.core.security import get_current_user

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
    # 1. Resolve accounts owned by the user (optionally filtered by provider)
    stmt_accounts = select(MailAccount.id).where(
        MailAccount.user_id == current_user.id,
        MailAccount.deliver_to_dashboard == True
    )
    if provider:
        stmt_accounts = stmt_accounts.where(MailAccount.provider == provider)
    res_accounts = await db.execute(stmt_accounts)
    user_account_ids = res_accounts.scalars().all()
    
    if not user_account_ids:
        return {
            "total": 0,
            "page": page,
            "limit": limit,
            "total_pages": 0,
            "emails": []
        }
        
    # 2. Apply mailbox filter if requested
    target_account_ids = user_account_ids
    if account_id:
        try:
            filter_account_uuid = uuid.UUID(account_id)
            if filter_account_uuid not in user_account_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to requested mailbox or provider mismatch."
                )
            target_account_ids = [filter_account_uuid]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid account_id UUID format."
            )
            
    # 3. Build query filters
    where_clauses = [Email.mail_account_id.in_(target_account_ids)]
    
    if is_read is not None:
        where_clauses.append(Email.is_read == is_read)
        
    if search:
        search_term = f"%{search.lower()}%"
        where_clauses.append(
            Email.subject.ilike(search_term) |
            Email.from_name.ilike(search_term) |
            Email.from_email.ilike(search_term) |
            Email.snippet.ilike(search_term)
        )
        
    # 4. Query total count
    count_stmt = select(func.count()).select_from(Email).where(*where_clauses)
    res_count = await db.execute(count_stmt)
    total = res_count.scalar() or 0
    
    # 5. Fetch paginated records ordered by received_at desc
    offset = (page - 1) * limit
    select_stmt = select(Email).where(*where_clauses).order_by(
        Email.received_at.desc()
    ).offset(offset).limit(limit)
    
    res_emails = await db.execute(select_stmt)
    emails = res_emails.scalars().all()
    
    total_pages = (total + limit - 1) // limit
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "emails": [
            {
                "id": str(email.id),
                "mail_account_id": str(email.mail_account_id),
                "message_id": email.message_id,
                "subject": email.subject,
                "from_email": email.from_email,
                "from_name": email.from_name,
                "received_at": email.received_at.isoformat() if email.received_at else None,
                "snippet": email.snippet,
                "has_attachment": email.has_attachment,
                "is_read": email.is_read
            }
            for email in emails
        ]
    }

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
        "body_html": email.body_html,
        "body_text": email.body_text,
        "created_at": email.created_at.isoformat() if email.created_at else None
    }
