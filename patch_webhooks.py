import os

target = "backend/app/api/routes/webhooks.py"
with open(target, "r") as f:
    content = f.read()

new_imports = """
from fastapi import APIRouter, HTTPException, Request, Header, Query, Response, BackgroundTasks
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import OutlookSubscription
from app.core.encryption import decrypt_token
import secrets
"""
content = content.replace("from fastapi import APIRouter, HTTPException, Request, Header", new_imports.strip())

outlook_route = """

@router.api_route("/outlook", methods=["GET", "POST"])
async def outlook_webhook(
    request: Request,
    validationToken: str = Query(None),
):
    \"\"\"
    Microsoft Graph Webhook endpoint for Outlook mail notifications.
    \"\"\"
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
"""

if "outlook_webhook" not in content:
    content += outlook_route

with open(target, "w") as f:
    f.write(content)

print("webhooks patched")
