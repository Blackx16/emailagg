from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "emailagg",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
        "app.workers.sync_tasks",
        "app.workers.notification_tasks",
        "app.workers.forwarding_tasks",
        "app.workers.outlook_webhook_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Fair distribution: don't pre-fetch tasks; process one at a time per worker slot
    worker_prefetch_multiplier=1,
    # Acknowledge task only after completion — safe re-queue on crash
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # ── Queue routing ────────────────────────────────────────────────────────
    # Each pipeline is isolated so a slow SMTP call never blocks Telegram alerts
    # and a heavy IMAP poll never delays sync orchestration.
    task_routes={
        "app.workers.sync_tasks.orchestrate_accounts": {"queue": "maintenance"},
        "app.workers.sync_tasks.sync_account": {"queue": "sync"},
        "app.workers.notification_tasks.*": {"queue": "notifications"},
        "app.workers.forwarding_tasks.*": {"queue": "forwarding"},
        "app.workers.outlook_webhook_tasks.*": {"queue": "outlook_webhooks"},
    },
    # ── Beat schedule ────────────────────────────────────────────────────────
    # A single lightweight orchestrator fires every SYNC_POLL_INTERVAL seconds.
    # It queries the DB for all active accounts and distributes individual sync
    # tasks with even spacing + random jitter so load is spread across the full
    # polling window rather than hitting all at t=0 (thundering herd).
    beat_schedule={
        "orchestrate-accounts": {
            "task": "app.workers.sync_tasks.orchestrate_accounts",
            "schedule": settings.SYNC_POLL_INTERVAL,
            "options": {"queue": "maintenance"},
        },
        "renew-outlook-subscriptions": {
            "task": "app.workers.outlook_webhook_tasks.renew_expiring_outlook_subscriptions",
            "schedule": 12 * 60 * 60,
            "options": {"queue": "outlook_webhooks"},
        },
    },
)
