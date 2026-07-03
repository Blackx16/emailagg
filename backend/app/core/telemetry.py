import logging
import time
from datetime import datetime
from typing import Optional, Any
import os

from sqlalchemy.ext.asyncio import AsyncSession
import sentry_sdk
from posthog import Posthog
from prometheus_client import Counter, Histogram

from app.db.models import SystemEvent
from app.core.config import settings

logger = logging.getLogger("emailagg.telemetry")

# Prometheus Metrics
EVENT_COUNTER = Counter("system_events_total", "Total system events emitted", ["service", "event_type", "severity"])
TASK_DURATION = Histogram("task_duration_seconds", "Duration of tasks in seconds", ["service", "event_type"])

class TelemetryClient:
    def __init__(self):
        self.posthog = None
        self.sentry_initialized = False

        if settings.POSTHOG_API_KEY:
            self.posthog = Posthog(settings.POSTHOG_API_KEY, host="https://app.posthog.com")
            
        if settings.SENTRY_DSN:
            sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=os.environ.get("ENV", "production"))
            self.sentry_initialized = True

    async def log_event(
        self,
        db: AsyncSession,
        service: str,
        event_type: str,
        severity: str = "info",
        user_id: Optional[Any] = None,
        worker: Optional[str] = None,
        duration_ms: Optional[int] = None,
        metadata_payload: Optional[dict] = None
    ):
        """
        Emits a telemetry event to:
        1. PostgreSQL (Mission Control Timeline)
        2. PostHog (Product Analytics)
        3. Sentry (Error Tracking)
        4. Prometheus (Metrics)
        5. Structured Logs
        """
        if metadata_payload is None:
            metadata_payload = {}

        # 1. Database
        event = SystemEvent(
            service=service,
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            worker=worker,
            duration_ms=duration_ms,
            metadata_payload=metadata_payload
        )
        db.add(event)
        
        # 2. Prometheus
        EVENT_COUNTER.labels(service=service, event_type=event_type, severity=severity).inc()
        if duration_ms is not None:
            TASK_DURATION.labels(service=service, event_type=event_type).observe(duration_ms / 1000.0)

        # 3. PostHog
        if self.posthog and user_id:
            try:
                self.posthog.capture(
                    str(user_id),
                    event_type,
                    properties={
                        "service": service,
                        "severity": severity,
                        "worker": worker,
                        "duration_ms": duration_ms,
                        **metadata_payload
                    }
                )
            except Exception as e:
                logger.warning(f"PostHog capture failed: {e}")

        # 4. Sentry
        if self.sentry_initialized and severity in ["error", "critical"]:
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("service", service)
                scope.set_tag("event_type", event_type)
                if user_id:
                    scope.set_user({"id": str(user_id)})
                if worker:
                    scope.set_tag("worker", worker)
                scope.set_extra("metadata", metadata_payload)
                sentry_sdk.capture_message(f"[{service}] {event_type}", level=severity)

        # 5. Logs
        log_msg = f"Event: {event_type} | Service: {service} | Severity: {severity}"
        if severity == "error" or severity == "critical":
            logger.error(f"{log_msg} | Metadata: {metadata_payload}")
        else:
            logger.info(f"{log_msg} | Metadata: {metadata_payload}")


telemetry = TelemetryClient()
