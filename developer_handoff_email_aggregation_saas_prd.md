# Developer Handoff Document
# Telegram-Based Unified Email Aggregation SaaS

## Project Overview

We are building a scalable SaaS platform that allows users to connect multiple email accounts (primarily Microsoft Outlook / Microsoft 365 / Gmail / IMAP providers) into a centralized system.

The system should:
- aggregate emails from multiple inboxes
- provide Telegram notifications
- provide a centralized dashboard
- avoid Microsoft forwarding restrictions
- support scaling to hundreds/thousands of accounts
- eventually become a SaaS product

The platform is NOT a simple forwarding tool.

This is intended to evolve into:
- unified inbox infrastructure
- agency communication hub
- multi-account notification system
- AI-assisted inbox management platform

---

# Main Product Goals

## Core Features

### Phase 1 (MVP)

Users should be able to:
- connect Outlook accounts
- connect Gmail accounts
- receive Telegram notifications for incoming emails
- view connected accounts in dashboard
- manage accounts
- disconnect accounts
- aggregate email metadata centrally

System should:
- continuously sync inboxes
- securely store OAuth tokens
- avoid email forwarding rules
- support multiple accounts per user
- support basic admin panel

---

# High-Level Architecture

```text
Telegram Bot
      ↓
FastAPI Backend
      ↓
PostgreSQL + Redis
      ↓
Mail Sync Workers
      ↓
Microsoft Graph API / IMAP
      ↓
Mailcow Infrastructure
```

---

# IMPORTANT PRODUCT DIRECTION

Do NOT build this as:
- traditional forwarding system
- Outlook forwarding rule automation
- SMTP relay product

Instead:
- emails are fetched via OAuth/API/IMAP
- notifications are generated internally
- inboxes are synchronized

The product must NOT depend on Outlook forwarding.

---

# Preferred Tech Stack

## Backend

### Required
- Python 3.12+
- FastAPI
- SQLAlchemy
- Alembic

### Queue / Background Jobs
- Redis
- Celery OR RQ

### Database
- PostgreSQL

### Mail Infrastructure
- Mailcow (Dockerized)

### Telegram Bot
- aiogram

### Frontend
- Next.js OR React

### Reverse Proxy
- Nginx

### Deployment
- Docker Compose initially

---

# WHY THIS STACK

FastAPI:
- async support
- excellent performance
- clean API development
- strong Python ecosystem

Python:
- email ecosystem mature
- Microsoft Graph integrations easier
- AI integrations later
- automation-friendly

Redis:
- queueing
- caching
- rate limiting
- session management

Mailcow:
- mature mail infrastructure
- less sysadmin complexity
- Dockerized
- production-ready

---

# Authentication Requirements

## CRITICAL REQUIREMENT

DO NOT collect user passwords manually.

NO plain text credentials.

NO Telegram credential TXT uploads.

The system MUST use OAuth.

---

# Microsoft OAuth Flow

Required:
- Microsoft OAuth2
- refresh token storage
- automatic token renewal

Flow:

```text
User clicks Connect Outlook
       ↓
Redirect to Microsoft OAuth
       ↓
User authorizes application
       ↓
Backend receives tokens
       ↓
Encrypted token storage
       ↓
Worker starts synchronization
```

---

# Gmail OAuth Flow

Same architecture.

Use:
- Google OAuth2
- Gmail API where needed

---

# Security Requirements

## Mandatory

### Token Encryption
Use:
- AES-256
OR
- Fernet encryption

Tokens MUST be encrypted at rest.

---

### HTTPS
Entire platform must run behind HTTPS.

Use:
- Cloudflare
- Let's Encrypt
- Nginx reverse proxy

---

### Isolation
Mail workers must run isolated from API layer.

---

### Logging
Need:
- API logs
- worker logs
- auth logs
- failure logs

---

### Abuse Protection
Need:
- rate limiting
- spam prevention
- user account limits
- account verification

---

# Telegram Bot Requirements

## Telegram is NOT the main app

Telegram is:
- onboarding interface
- notification layer
- quick actions layer

Main management should happen via:
- web dashboard
OR
- Telegram Mini App

---

# Telegram Bot Features

## MVP Features

### Commands

```text
/start
/connect
/accounts
/disconnect
/help
/settings
```

---

## Notifications

Example:

```text
📩 New Email

From: Amazon AWS
Subject: Billing Alert
Mailbox: [email protected]

Open Dashboard
```

---

## Future Telegram Features

### Planned
- reply from Telegram
- AI summaries
- attachment previews
- priority alerts
- OTP extraction
- filtering rules

---

# Email Synchronization Strategy

## IMPORTANT

DO NOT use Outlook forwarding rules.

---

# Preferred Architecture

## Microsoft Accounts

### Preferred
Use:
- Microsoft Graph API

Why:
- modern
- scalable
- webhook support
- less polling
- enterprise-safe

---

## IMAP Support

Fallback support required for:
- legacy providers
- custom domains
- unsupported services

Use:
- aioimaplib
OR
- imapclient

---

# Sync Model

## Initial Sync

Fetch:
- latest emails
- folders
- metadata

Store:
- subject
- sender
- timestamp
- message ID
- mailbox ID

Attachments optional in MVP.

---

## Live Sync

Preferred:
- webhook/event-driven

Fallback:
- periodic polling

---

# Database Design

## users

```sql
id
telegram_id
email
plan
created_at
updated_at
```

---

## mail_accounts

```sql
id
user_id
provider
email
access_token_encrypted
refresh_token_encrypted
status
last_sync
created_at
```

---

## emails

```sql
id
mail_account_id
message_id
subject
from_email
received_at
snippet
has_attachment
is_read
```

---

## notifications

```sql
id
user_id
email_id
sent_at
status
```

---

# Infrastructure Requirements

## MVP VPS

Minimum:
- 4 vCPU
- 8GB RAM
- 100GB SSD

---

# Production Scaling Strategy

## Stage 1
Single VPS.

Everything Dockerized.

---

## Stage 2
Separate:
- API server
- worker server
- database server
- mail server

---

## Stage 3
Container orchestration.

Potential:
- Kubernetes
- autoscaling workers
- distributed queues

---

# Deployment Requirements

## Required

Docker Compose setup for:
- backend
- database
- Redis
- Mailcow
- worker services
- Telegram bot

---

# Monitoring

Preferred:
- Grafana
- Prometheus
- Loki

Need:
- server monitoring
- worker monitoring
- queue monitoring
- sync failure monitoring

---

# Admin Dashboard Requirements

## Required Features

### User Management
- total users
- connected accounts
- account status
- failed syncs

### System Monitoring
- worker status
- queue size
- API health
- sync latency

### Abuse Monitoring
- excessive polling
- suspicious activity
- account abuse

---

# User Dashboard Requirements

## MVP

### Account Management
- connect account
- disconnect account
- view sync status

### Email Overview
- latest emails
- account-wise filtering
- notification settings

---

# SaaS Planning

## Initial Plans

| Plan | Accounts |
|---|---|
| Free | 3 |
| Pro | 25 |
| Agency | 100 |

---

# Billing Integration

Preferred:
- Razorpay initially
- Stripe later

Need:
- subscription handling
- account limits
- plan enforcement

---

# Future AI Features

Not required for MVP.

Planned features:
- email summarization
- priority classification
- AI-generated replies
- spam filtering
- smart categorization
- workflow automations

---

# IMPORTANT ENGINEERING REQUIREMENTS

## Reliability First

Most important priorities:

1. sync stability
2. authentication reliability
3. secure token handling
4. scalability
5. observability

NOT UI animations.

---

# Important Constraints

## Avoid
- credential scraping
- Outlook forwarding rules
- SMTP relay dependency
- storing raw passwords

---

# Expected Deliverables

Developer/team should provide:

## Backend
- production-ready API
- authentication system
- sync workers
- Telegram integration

## Infrastructure
- Docker deployment
- Mailcow setup
- database setup
- monitoring setup

## Frontend
- dashboard
- onboarding flow
- account management

## Documentation
- deployment docs
- environment setup
- API documentation
- scaling notes

---

# Preferred Development Approach

## Phase 1
Core architecture.

## Phase 2
OAuth + synchronization.

## Phase 3
Telegram integration.

## Phase 4
Dashboard.

## Phase 5
Billing + production hardening.

---

# MVP Success Criteria

MVP considered successful if:

- users can connect Outlook/Gmail accounts
- emails sync reliably
- Telegram notifications work
- multiple accounts supported
- system survives continuous operation
- no forwarding rules required

---

# Long-Term Product Vision

This product should eventually evolve into:

## Unified Inbox Infrastructure Platform

Potential future positioning:
- agency communication hub
- AI inbox assistant
- email intelligence platform
- multi-account notification engine
- centralized inbox operating system

---

# Final Notes For Developer

This project must be designed with scalability in mind from the beginning.

Even if MVP is small, architecture should support:
- thousands of connected accounts
- worker scaling
- webhook/event processing
- SaaS billing
- enterprise onboarding

Security and authentication quality are extremely important.

The project should feel like:
- a modern infrastructure product
NOT
- a hacked-together forwarding script.

