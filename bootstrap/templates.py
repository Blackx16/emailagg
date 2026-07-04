"""
templates.py — Template registry and content builders for the Engineering OS Bootstrapper.

Defines the full EmailAgg Confluence page hierarchy and Jira bootstrap data
as Python dataclasses, kept separate from YAML manifests for programmatic use.

Also re-exports template rendering helpers for convenience.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from bootstrap.jira import ComponentSpec, EpicSpec, VersionSpec


# ---------------------------------------------------------------------------
# EmailAgg Jira Bootstrap Data
# ---------------------------------------------------------------------------

EMAILAGG_EPICS: list[EpicSpec] = [
    EpicSpec(
        name="Product",
        description="Product vision, roadmap, release planning, and business metrics for EmailAgg.",
        labels=["product", "beta"],
    ),
    EpicSpec(
        name="Authentication",
        description="OAuth2 flows for Gmail and Microsoft, IMAP credential management, token refresh, and Fernet encryption.",
        labels=["backend", "security"],
    ),
    EpicSpec(
        name="Email Sync Engine",
        description="IMAP polling, IDLE push, Microsoft Graph webhooks, Gmail Pub/Sub, and sync deduplication.",
        labels=["backend", "worker"],
    ),
    EpicSpec(
        name="Email Forwarding Engine",
        description="SMTP relay, Google API send, Microsoft Graph sendMail, HTML rewriting, and forwarding rules.",
        labels=["backend", "worker"],
    ),
    EpicSpec(
        name="Mission Control Dashboard",
        description="Real-time admin dashboard: system health, user telemetry, CPU/storage graphs, and operator controls.",
        labels=["frontend", "infra"],
    ),
    EpicSpec(
        name="Telegram Bot",
        description="aiogram bot: /start, /connect, /rules, /settings, /disconnect commands, and WebApp integration.",
        labels=["backend", "api"],
    ),
    EpicSpec(
        name="Infrastructure",
        description="Docker Compose orchestration, Nginx SSL proxy, Redis configuration, and VPS provisioning.",
        labels=["infra", "docker"],
    ),
    EpicSpec(
        name="Monitoring & Observability",
        description="Celery Flower, log aggregation, Google Drive backup scripts, health check endpoints.",
        labels=["infra", "monitoring"],
    ),
    EpicSpec(
        name="Security",
        description="Security hardening: auth middleware, internal API protection, Nginx proxy blocking, rate limiting.",
        labels=["security", "backend"],
    ),
    EpicSpec(
        name="Deployment",
        description="Production deployment: SSL, domain config, Docker build pipeline, and environment management.",
        labels=["infra", "deploy"],
    ),
    EpicSpec(
        name="Documentation",
        description="Engineering OS: Confluence page hierarchy, ADRs, runbooks, API docs, and architecture diagrams.",
        labels=["documentation"],
    ),
    EpicSpec(
        name="Technical Debt",
        description="Known technical debt items, refactoring backlog, and code quality improvements.",
        labels=["tech-debt"],
    ),
]

EMAILAGG_COMPONENTS: list[ComponentSpec] = [
    ComponentSpec(name="Backend", description="FastAPI application, REST API routes, and core business logic"),
    ComponentSpec(name="Frontend", description="Next.js dashboard client and Telegram Mini App"),
    ComponentSpec(name="Worker", description="Celery task workers: sync, notify, forward, beat scheduler"),
    ComponentSpec(name="Infrastructure", description="Docker Compose, Nginx, VPS provisioning, and networking"),
    ComponentSpec(name="Database", description="PostgreSQL schema, Alembic migrations, and query optimisation"),
    ComponentSpec(name="Redis", description="Redis configuration, rate limiting, locking, and caching"),
    ComponentSpec(name="Docker", description="Dockerfiles, multi-stage builds, and image management"),
    ComponentSpec(name="Celery", description="Celery configuration, queue routing, and task monitoring"),
    ComponentSpec(name="Monitoring", description="Flower, health endpoints, log backup, and alerting"),
    ComponentSpec(name="Security", description="Auth middleware, Fernet encryption, and security hardening"),
    ComponentSpec(name="Website", description="GitHub Pages landing page"),
    ComponentSpec(name="Mission Control", description="Internal operator dashboard for system monitoring"),
    ComponentSpec(name="Telegram", description="aiogram bot handlers, commands, and WebApp"),
    ComponentSpec(name="Google API", description="Gmail OAuth, Google Drive, and Google REST API integrations"),
    ComponentSpec(name="Microsoft Graph", description="Microsoft OAuth, Outlook API, and Graph API integrations"),
]

EMAILAGG_VERSIONS: list[VersionSpec] = [
    VersionSpec(name="Private Beta", description="Initial private beta — limited user testing"),
    VersionSpec(name="Production Beta", description="Public beta — broader user access with known limitations"),
    VersionSpec(name="v1.0", description="First stable production release"),
]

EMAILAGG_LABELS: list[str] = [
    "backend",
    "frontend",
    "infra",
    "security",
    "worker",
    "api",
    "bug",
    "feature",
    "documentation",
    "tech-debt",
    "beta",
    "release",
]


# ---------------------------------------------------------------------------
# EmailAgg Confluence Page Hierarchy
# (mirrors the YAML manifest — defined here for Python-native access)
# ---------------------------------------------------------------------------

EMAILAGG_CONFLUENCE_HIERARCHY: dict[str, Any] = {
    "EmailAgg": {
        "Home": {},
        "Product": {
            "Product Vision": {},
            "Roadmap": {},
            "Release Notes": {},
            "Changelog": {},
        },
        "Architecture": {
            "Overview": {},
            "Backend": {},
            "Frontend": {},
            "Database": {},
            "Queue Architecture": {},
            "Infrastructure": {},
            "Deployment": {},
            "External Services": {},
        },
        "ADRs": {
            "ADR-000 Template": {},
            "ADR-001 Use PostgreSQL as Primary Database": {},
            "ADR-002 OAuth2 for Gmail and Microsoft Authentication": {},
            "ADR-003 Celery with Redis as Task Queue": {},
            "ADR-004 Fernet Encryption for Credential Storage": {},
            "ADR-005 IMAP IDLE for Real-Time Email Sync": {},
            "ADR-006 Microsoft Graph API over IMAP for Outlook": {},
            "ADR-007 Docker Compose for Production Orchestration": {},
            "ADR-008 Nginx as Reverse Proxy with SSL Termination": {},
            "ADR-009 aiogram for Telegram Bot Framework": {},
            "ADR-010 Next.js for Frontend Dashboard": {},
            "ADR-011 Redis Rate Limiting and Distributed Locking": {},
            "ADR-012 Alembic for Database Migration Management": {},
            "ADR-013 Google Drive for Log Backups": {},
            "ADR-014 4-Queue Celery Architecture": {},
            "ADR-015 FastAPI for REST API Backend": {},
            "ADR-016 In-Memory IMAP Parser for HTML Email Forwarding": {},
            "ADR-017 Flower for Celery Worker Monitoring": {},
            "ADR-018 Security Hardening Strategy": {},
            "ADR-019 Telegram WebApp for Dashboard Access": {},
            "ADR-020 Mission Control Internal Dashboard": {},
        },
        "API": {
            "REST API": {},
            "Internal APIs": {},
            "Authentication": {},
            "Webhooks": {},
        },
        "Infrastructure": {
            "Docker": {},
            "Redis": {},
            "Celery": {},
            "VPS": {},
            "Monitoring": {},
            "Logging": {},
            "Backups": {},
            "Nginx": {},
        },
        "Operations": {
            "Runbooks": {
                "Runbook — Deploy to Production": {},
                "Runbook — Restart Celery Workers": {},
                "Runbook — Database Migration": {},
                "Runbook — Redis Flush and Recovery": {},
                "Runbook — SSL Certificate Renewal": {},
                "Runbook — Log Backup Verification": {},
            },
            "Incident Response": {},
            "Disaster Recovery": {},
            "Maintenance": {},
        },
        "Development": {
            "Repository Structure": {},
            "Environment Variables": {},
            "Coding Standards": {},
            "Technical Debt": {},
        },
    }
}

ENGINEERING_OS_ROOT_HIERARCHY: dict[str, Any] = {
    "Engineering": {
        "Projects": {
            **EMAILAGG_CONFLUENCE_HIERARCHY,
        },
        "Templates": {},
        "Engineering Handbook": {},
        "Architecture": {},
        "Runbooks": {},
        "Standards": {},
        "Decision Records": {},
    }
}
