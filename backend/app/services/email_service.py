import uuid
from typing import Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.models import User, MailAccount, Email

async def get_paginated_emails(
    db: AsyncSession,
    current_user: User,
    account_id: str | None = None,
    provider: str | None = None,
    is_read: bool | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict[str, Any]:
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
