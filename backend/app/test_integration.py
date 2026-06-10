import asyncio
import sys
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

# App imports
from app.db.session import get_db, AsyncSessionLocal
from app.db.models import User, MailAccount, Email, ForwardingRule
from app.services.forwarding_service import extract_otp, _matches, check_and_forward
from app.core.redis import get_redis


def test_otp_extraction():
    print("--- Testing OTP Extraction ---")
    test_cases = [
        ("Your verification code is 123456", "Please enter 123456 to verify your login.", "123456"),
        ("Netflix verification code: 987654", "Use this code to login to Netflix", "987654"),
        ("Confirm your registration", "Your secure pin is: ABCD12", "ABCD12"),
        ("Google Verification Code", "Your Google verification code is 432109.", "432109"),
        ("Your single-use code is 88775", "Use 88775 to verify.", "88775"),
        ("Normal Subject", "Just a regular email with no codes in it", None),
    ]

    for subj, snippet, expected in test_cases:
        result = extract_otp(subj, snippet)
        print(f"Subject: '{subj}' | Snippet: '{snippet}' -> Extracted: {result} (Expected: {expected})")
        assert result == expected, f"Expected {expected}, got {result}"

    print("✅ OTP extraction test passed successfully!")


def test_rule_matching():
    print("\n--- Testing Rule Matching Logic ---")
    # Mock Email object (using simple attribute class since Email is a SQLAlchemy model)
    class MockEmail:
        def __init__(self, subject, from_email, snippet):
            self.subject = subject
            self.from_email = from_email
            self.snippet = snippet

    email = MockEmail(
        subject="Your OTP is 1234",
        from_email="noreply@netflix.com",
        snippet="Netflix OTP is 1234"
    )

    # Test Subject Contains
    rule1 = ForwardingRule(condition_subject_contains="OTP", forward_to_email="test@domain.com")
    rule2 = ForwardingRule(condition_subject_contains="Google", forward_to_email="test@domain.com")
    assert _matches(email, rule1) is True
    assert _matches(email, rule2) is False

    # Test From Email
    rule3 = ForwardingRule(condition_from_email="noreply@netflix.com", forward_to_email="test@domain.com")
    rule4 = ForwardingRule(condition_from_email="other@netflix.com", forward_to_email="test@domain.com")
    assert _matches(email, rule3) is True
    assert _matches(email, rule4) is False

    # Test From Domain
    rule5 = ForwardingRule(condition_from_domain="netflix.com", forward_to_email="test@domain.com")
    rule6 = ForwardingRule(condition_from_domain="gmail.com", forward_to_email="test@domain.com")
    assert _matches(email, rule5) is True
    assert _matches(email, rule6) is False

    # Test Body Contains
    rule7 = ForwardingRule(condition_body_contains="Netflix", forward_to_email="test@domain.com")
    rule8 = ForwardingRule(condition_body_contains="Disney", forward_to_email="test@domain.com")
    assert _matches(email, rule7) is True
    assert _matches(email, rule8) is False

    print("✅ Rule matching logic test passed successfully!")


async def test_db_uniqueness():
    print("\n--- Testing DB Uniqueness Constraint ---")
    
    # We open a direct session from the sessionmanager
    async with AsyncSessionLocal() as db:
        # Get or create a test user
        stmt = select(User).where(User.telegram_id == 999999)
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            user = User(telegram_id=999999, plan="free")
            db.add(user)
            await db.commit()
            await db.refresh(user)

        # Get or create a mail account
        stmt = select(MailAccount).where(MailAccount.user_id == user.id)
        res = await db.execute(stmt)
        account = res.scalars().first()
        if not account:
            account = MailAccount(
                user_id=user.id,
                provider="imap",
                email="test_unique@lvh.me",
                status="active"
            )
            db.add(account)
            await db.commit()
            await db.refresh(account)

        # Generate a unique message_id for this test run
        message_id = f"test-unique-msg-{uuid.uuid4()}"

        print(f"Inserting first email with message_id: {message_id}")
        email1 = Email(
            mail_account_id=account.id,
            message_id=message_id,
            subject="First email",
            from_name="Test",
            from_email="test@lvh.me",
            snippet="Snippet",
            received_at=datetime.now(timezone.utc),
            is_read=False
        )
        db.add(email1)
        await db.commit()
        print("First insert successful!")

        # Try to insert identical message_id under the same account
        print("Inserting second email with identical message_id...")
        email2 = Email(
            mail_account_id=account.id,
            message_id=message_id,
            subject="Second email (duplicate)",
            from_name="Test",
            from_email="test@lvh.me",
            snippet="Snippet",
            received_at=datetime.now(timezone.utc),
            is_read=False
        )
        
        try:
            db.add(email2)
            await db.commit()
            # If it reaches here, uniqueness constraint is not working!
            print("❌ ERROR: Database allowed inserting duplicate emails!")
            sys.exit(1)
        except IntegrityError as e:
            await db.rollback()
            print("✅ Got expected IntegrityError due to uniqueness constraint violation!")
            print(f"Error message: {str(e)}")

        # Clean up
        await db.delete(email1)
        await db.commit()
        print("Cleaned up test email.")


async def test_redis_forward_rate_limit():
    print("\n--- Testing Redis Forward Rate Limiter ---")
    redis = await get_redis()
    
    test_user_id = uuid.uuid4()
    hour_key = datetime.now().strftime("%Y%m%d%H")
    redis_key = f"forward_rate:{test_user_id}:{hour_key}"
    
    # Reset key
    await redis.delete(redis_key)
    
    # Increment up to 52 times
    limit_reached = False
    for i in range(1, 55):
        count = await redis.incr(redis_key)
        if i == 1:
            await redis.expire(redis_key, 3600)
            
        if count > 50:
            limit_reached = True
            print(f"Increment {i}: Limit exceeded! (Redis count={count})")
            break
            
    assert limit_reached is True, "Expected forwarding to be rate limited at > 50"
    print("✅ Redis forward rate limit test passed successfully!")


async def main():
    test_otp_extraction()
    test_rule_matching()
    await test_db_uniqueness()
    await test_redis_forward_rate_limit()
    print("\n🎉 All integration tests run inside the container passed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
