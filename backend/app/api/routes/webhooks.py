import hashlib
import hmac
import logging
from fastapi import APIRouter, HTTPException, Request, Header, Query, Response, BackgroundTasks
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import OutlookSubscription
from app.core.encryption import decrypt_token
import secrets
from typing import Annotated

from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Signature verification helpers ───────────────────────────────────────────

def verify_stripe_signature(
    payload: bytes,
    sig_header: str,
    secret: str,
    tolerance_seconds: int = 300,
) -> bool:
    """
    Verify a Stripe webhook signature (Stripe-Signature header).

    Stripe signs payloads using HMAC-SHA256 with a timestamp prefix to prevent
    replay attacks.  The tolerance_seconds window (default 5 min) rejects
    signatures older than that.

    Returns True if the signature is valid, False otherwise.
    Usage:
        if not verify_stripe_signature(body, sig_header, settings.STRIPE_WEBHOOK_SECRET):
            raise HTTPException(status_code=400, detail="Invalid signature.")
    """
    import time

    try:
        parts = {k: v for k, v in (part.split("=", 1) for part in sig_header.split(",") if "=" in part)}
        timestamp = int(parts.get("t", 0))
        v1_signatures = [v for k, v in parts.items() if k == "v1"]
    except Exception:
        return False

    # Check timestamp tolerance
    if abs(time.time() - timestamp) > tolerance_seconds:
        logger.warning("Stripe webhook timestamp outside tolerance window.")
        return False

    # Compute expected signature
    signed_payload = f"{timestamp}.".encode() + payload
    expected = hmac.new(
        secret.encode(),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()

    return any(hmac.compare_digest(expected, sig) for sig in v1_signatures)


def verify_generic_hmac(payload: bytes, sig_header: str, secret: str) -> bool:
    """
    Verify a generic HMAC-SHA256 webhook signature.
    The signature header should be: sha256=<hex_digest>
    Compatible with GitHub, Razorpay, and many other providers.
    """
    try:
        algo, provided_sig = sig_header.split("=", 1)
        if algo != "sha256":
            return False
    except ValueError:
        return False

    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, provided_sig)


# ── Webhook endpoints ─────────────────────────────────────────────────────────

@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: Annotated[str | None, Header(alias="stripe-signature")] = None,
):
    """
    Stripe payment webhook endpoint.

    Signature verification is implemented and enforced.
    Handler logic will be added once the Stripe integration is configured.

    To activate:
    1. Set STRIPE_WEBHOOK_SECRET in .env
    2. Implement the event handlers in this function
    """
    if not stripe_signature:
        logger.warning("Stripe webhook received without signature header.")
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header.")

    # Only verify if secret is configured (skip in dev if not set)
    stripe_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", None)
    if stripe_secret:
        body = await request.body()
        if not verify_stripe_signature(body, stripe_signature, stripe_secret):
            logger.warning("Stripe webhook signature verification failed.")
            raise HTTPException(status_code=400, detail="Invalid webhook signature.")

    # ── Event handlers go here ───────────────────────────────────────────────
    # payload = await request.json()
    # event_type = payload.get("type")
    # if event_type == "checkout.session.completed":
    #     await handle_checkout_completed(payload["data"]["object"])
    # elif event_type == "customer.subscription.deleted":
    #     await handle_subscription_cancelled(payload["data"]["object"])

    logger.info("Stripe webhook received — handler not yet implemented.")
    return {"status": "received"}


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: Annotated[str | None, Header(alias="x-razorpay-signature")] = None,
):
    """
    Razorpay payment webhook endpoint.

    Ready for implementation when Razorpay is configured.
    """
    if not x_razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing X-Razorpay-Signature header.")

    razorpay_secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", None)
    if razorpay_secret:
        body = await request.body()
        sig = f"sha256={x_razorpay_signature}"
        if not verify_generic_hmac(body, sig, razorpay_secret):
            logger.warning("Razorpay webhook signature verification failed.")
            raise HTTPException(status_code=400, detail="Invalid webhook signature.")

    logger.info("Razorpay webhook received — handler not yet implemented.")
    return {"status": "received"}


@router.api_route("/outlook", methods=["GET", "POST"])
async def outlook_webhook(
    request: Request,
    validationToken: str = Query(None),
):
    """
    Microsoft Graph Webhook endpoint for Outlook mail notifications.
    """
    # 1. Validation Handshake
    if validationToken:
        return Response(content=validationToken, media_type="text/plain", status_code=200)
        
    if request.method == "GET":
        raise HTTPException(status_code=405, detail="Method Not Allowed")

    # 2. Process Notifications
    payload = await request.json()
    notifications = payload.get("value", [])
    
    if not notifications:
        return Response(status_code=202)

    from app.workers.outlook_webhook_tasks import process_outlook_notification

    async with AsyncSessionLocal() as db:
        for notif in notifications:
            sub_id = notif.get("subscriptionId")
            client_state = notif.get("clientState")
            resource_data = notif.get("resourceData", {})
            message_id = resource_data.get("id")
            
            if not sub_id or not client_state or not message_id:
                logger.warning("Incomplete notification payload received.")
                continue

            # Verify subscription and clientState
            stmt = select(OutlookSubscription).where(OutlookSubscription.subscription_id == sub_id, OutlookSubscription.status == "active")
            sub = (await db.execute(stmt)).scalar_one_or_none()
            
            if not sub:
                logger.warning("Webhook received for unknown or inactive subscription: %s", sub_id)
                continue
                
            try:
                expected_state = decrypt_token(sub.client_state_encrypted)
            except Exception as e:
                logger.error("Failed to decrypt client_state for subscription %s: %s", sub_id, e)
                continue

            if not secrets.compare_digest(expected_state, client_state):
                logger.warning("Invalid clientState for subscription %s", sub_id)
                continue

            # Enqueue the task
            process_outlook_notification.delay(sub_id, message_id)

    return Response(status_code=202)
