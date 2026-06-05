from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "emailagg",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.sync_tasks",
        "app.workers.notification_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,        # fair distribution
    task_acks_late=True,                 # ack after completion, not before
    task_reject_on_worker_lost=True,     # re-queue on crash
    task_routes={
        "app.workers.sync_tasks.*": {"queue": "sync"},
        "app.workers.notification_tasks.*": {"queue": "notifications"},
    },
    beat_schedule={
        # Poll all active accounts every SYNC_POLL_INTERVAL seconds
        "poll-all-accounts": {
            "task": "app.workers.sync_tasks.poll_all_accounts",
            "schedule": settings.SYNC_POLL_INTERVAL,
        },
    },
)
