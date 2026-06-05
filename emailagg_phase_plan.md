# EmailAgg — Phase-wise Development Plan
**Telegram-Based Unified Email Aggregation SaaS**

> This document covers every phase of the project in detail — what we're building, why we're doing it in that order, what files get written, what commands get run, and what "done" looks like before moving on.

---

## Overview

| Phase | Name | Core Goal |
|---|---|---|
| 1 | Core Architecture | Repo, Docker, DB, working API skeleton |
| 2 | OAuth + Mail Sync | Microsoft Graph + Gmail sync working end-to-end |
| 3 | Telegram Bot | Notifications live, onboarding via bot |
| 4 | Web Dashboard | Next.js frontend for account + email management |
| 5 | Billing + Production Hardening | Razorpay subscriptions, monitoring, deployment |

Each phase builds on the previous one. **Do not skip ahead.** A broken sync (Phase 2) means a broken bot (Phase 3). Reliability of the data pipeline matters more than any UI.

---

## Phase 1 — Core Architecture

### What we're doing

Setting up the entire skeleton of the project before writing any real business logic. This means: Docker Compose running locally, PostgreSQL and Redis healthy, all four database tables created via Alembic migration, and the FastAPI server responding to a health check.

This phase is already done via the scaffold. But here's exactly what was set up and why.

### Services in Docker Compose

| Service | Image / Build | Purpose |
|---|---|---|
| `db` | `postgres:16-alpine` | Primary data store |
| `redis` | `redis:7-alpine` | Celery broker + result backend + rate limiting |
| `backend` | `./backend` | FastAPI API server |
| `worker` | `./backend` | Celery sync + notification worker |
| `beat` | `./backend` | Celery beat scheduler (periodic tasks) |
| `flower` | `./backend` | Celery monitoring UI |
| `bot` | `./bot` | aiogram Telegram bot |
| `nginx` | `nginx:alpine` | HTTPS reverse proxy |

`db`, `redis`, `worker`, and `beat` are on an **internal** Docker network — no direct internet access. Only `backend`, `flower`, and `nginx` are on the external network. This is a security requirement from the PRD.

### Database schema

Four tables, all with UUIDs as primary keys:

**`users`** — one row per Telegram user who registers.  
Fields: `id`, `telegram_id` (unique), `email`, `plan` (free/pro/agency), `is_active`, `is_admin`, `created_at`, `updated_at`.  
The `plan` field drives account limits: free=3, pro=25, agency=100.

**`mail_accounts`** — one row per connected inbox.  
Fields: `id`, `user_id` (FK), `provider` (microsoft/google/imap), `email`, `access_token_encrypted`, `refresh_token_encrypted`, `token_expires_at`, `imap_host`, `imap_port`, `status`, `last_sync`, `error_message`.  
Tokens are **never stored as plaintext** — always Fernet-encrypted before insertion.

**`emails`** — one row per email fetched from any inbox.  
Fields: `id`, `mail_account_id` (FK), `message_id` (provider's ID, indexed), `subject`, `from_email`, `from_name`, `received_at`, `snippet`, `has_attachment`, `is_read`, `notified`.  
`notified` is a boolean flag that prevents double-sending Telegram notifications.

**`notifications`** — audit trail of every Telegram message sent.  
Fields: `id`, `user_id` (FK), `email_id` (FK), `sent_at`, `status` (pending/sent/failed), `error_message`.

### Encryption setup

`app/core/encryption.py` wraps Python's `cryptography.fernet.Fernet`. Before any token goes into the `mail_accounts` table, it passes through `encrypt_token()`. When a sync worker needs to make an API call, it calls `decrypt_token()` first. The Fernet key lives only in `.env` and is never committed.

Generate your Fernet key once:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### How to verify Phase 1 is done

```bash
# 1. Copy and fill the env file
cp .env.example .env
bash scripts/generate_secrets.sh   # paste output into .env

# 2. Start infra
docker compose up db redis -d

# 3. Run migrations (creates all 4 tables)
docker compose run --rm backend alembic upgrade head

# 4. Start the API
docker compose up backend -d

# 5. Health check
curl http://localhost:8000/api/v1/health
# Expected: {"status": "ok", "db": "ok"}
```

If the health check returns `200`, Phase 1 is complete.

---

## Phase 2 — OAuth + Mail Sync

### What we're doing

This is the hardest and most important phase. We implement:

1. Microsoft OAuth2 flow (Azure app registration → token exchange → encrypted storage)
2. Google OAuth2 flow (Google Cloud Console → same pattern)
3. IMAP fallback for unsupported providers
4. Celery workers that actually fetch emails and store them in the DB

Everything in Phase 3, 4, and 5 depends on this working correctly. Don't rush it.

### Step 1 — Register OAuth apps

**Microsoft (Azure Portal)**

1. Go to [portal.azure.com](https://portal.azure.com) → Azure Active Directory → App Registrations → New Registration.
2. Name: `EmailAgg`, Supported account types: `Accounts in any organizational directory and personal Microsoft accounts`.
3. Redirect URI: `https://yourdomain.com/api/v1/auth/microsoft/callback` (Web platform).
4. After creation: note the **Application (client) ID** and **Directory (tenant) ID**.
5. Certificates & Secrets → New client secret → copy the **Value** immediately (shown once).
6. API Permissions → Add: `Mail.Read`, `offline_access`, `User.Read` → Grant admin consent.

Paste `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, `MICROSOFT_TENANT_ID=common` into `.env`.

**Google (Cloud Console)**

1. Go to [console.cloud.google.com](https://console.cloud.google.com) → New Project → `EmailAgg`.
2. APIs & Services → Enable: **Gmail API**.
3. OAuth consent screen → External → fill app name, support email, add scope: `https://www.googleapis.com/auth/gmail.readonly`.
4. Credentials → Create OAuth 2.0 Client ID → Web application.
5. Authorized redirect URIs: `https://yourdomain.com/api/v1/auth/google/callback`.
6. Download the JSON and note `client_id` and `client_secret`.

Paste `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` into `.env`.

### Step 2 — Implement OAuth routes

Write these in `backend/app/api/routes/auth.py`:

```
GET  /api/v1/auth/microsoft/login       → redirect to Microsoft consent page
GET  /api/v1/auth/microsoft/callback    → exchange code for tokens, encrypt, store in mail_accounts
GET  /api/v1/auth/google/login          → redirect to Google consent page
GET  /api/v1/auth/google/callback       → exchange code for tokens, encrypt, store in mail_accounts
POST /api/v1/auth/disconnect/{account_id} → set status=disconnected, clear tokens
```

For Microsoft, use the `msal` library (`ConfidentialClientApplication`). For Google, use `google_auth_oauthlib.flow.Flow`. Both follow the same pattern:

```
User visits /login → we build authorization URL → redirect them → they authorize →
provider redirects back to /callback with ?code=... → we exchange code for
access_token + refresh_token → encrypt both → INSERT into mail_accounts → 
enqueue first sync task
```

Write `backend/app/services/microsoft_auth.py` and `backend/app/services/google_auth.py` as thin wrappers around the OAuth libraries. Keep the route handlers thin — they should only call the service and return a response.

### Step 3 — Token refresh

Access tokens expire. Before every API call, check `token_expires_at`. If expired (or within 5 minutes of expiry), call the refresh endpoint:

- Microsoft: `msal` handles this automatically via `acquire_token_by_refresh_token()`.
- Google: `google.oauth2.credentials.Credentials.refresh()`.

Write `backend/app/services/token_service.py`:
```python
async def get_valid_access_token(account: MailAccount) -> str:
    # Check expiry, refresh if needed, re-encrypt and save new tokens, return plaintext token
```

This function is called by every sync worker before making API calls.

### Step 4 — Microsoft Graph sync

Write `backend/app/services/microsoft_sync.py`.

The Microsoft Graph endpoint for listing messages:
```
GET https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages
    ?$top=50
    &$select=id,subject,from,receivedDateTime,bodyPreview,hasAttachments,isRead
    &$orderby=receivedDateTime desc
```

Flow for each sync cycle:
1. Get valid access token (refresh if needed).
2. Fetch messages since `last_sync` timestamp (use `$filter=receivedDateTime ge {last_sync}`).
3. For each message, check if `message_id` already exists in `emails` table (skip if yes — deduplication).
4. INSERT new emails into `emails` table with `notified=False`.
5. Update `mail_accounts.last_sync` to now.
6. Enqueue a `send_telegram_notification` task for each new email.

**Webhook support (preferred over polling):** Microsoft Graph supports change notifications. Register a subscription:
```
POST https://graph.microsoft.com/v1.0/subscriptions
{
  "changeType": "created",
  "notificationUrl": "https://yourdomain.com/api/v1/webhooks/microsoft",
  "resource": "me/mailFolders/inbox/messages",
  "expirationDateTime": "<48 hours from now>"
}
```
When a webhook fires, Microsoft POSTs to `/api/v1/webhooks/microsoft`. Handle it in `app/api/routes/webhooks.py` — validate the token, then enqueue `sync_account` for that account. Webhooks expire every 48 hours — use Celery beat to renew them every 24 hours.

### Step 5 — Gmail sync

Write `backend/app/services/gmail_sync.py`.

Gmail uses `history.list` for incremental sync (much more efficient than listing all messages):
1. On first sync: use `messages.list` with `labelIds=INBOX`, store `historyId` from the response.
2. On subsequent syncs: call `history.list?startHistoryId={stored_id}` to get only changes.
3. For each added message, fetch it with `messages.get?format=metadata&metadataHeaders=Subject,From,Date`.
4. INSERT into `emails`, enqueue notification.

Gmail also supports push notifications via **Pub/Sub** (more complex setup, optional for MVP — polling is fine initially).

### Step 6 — IMAP fallback

Write `backend/app/services/imap_sync.py` using `aioimaplib`.

```python
async with aioimaplib.IMAP4_SSL(host, port) as client:
    await client.login(username, password)   # app password only, no plain passwords
    await client.select("INBOX")
    # SEARCH for messages since last_sync
    # FETCH metadata (envelope) for new message IDs
```

IMAP accounts require an **app password** (not the main password). Store it encrypted the same way as OAuth tokens in `access_token_encrypted`.

### Step 7 — Wire up Celery tasks

Fill in the stubs in `app/workers/sync_tasks.py`:

```python
@shared_task
def poll_all_accounts():
    # Query DB for all mail_accounts where status='active'
    # For each, enqueue sync_account.apply_async(args=[account_id])

@shared_task(bind=True, max_retries=3)
def sync_account(self, account_id: str):
    # Load account from DB
    # Route to correct service based on provider
    # On exception: update status='error', set error_message, then retry
```

And in `app/workers/notification_tasks.py`:

```python
@shared_task(bind=True, max_retries=5)
def send_telegram_notification(self, user_telegram_id: int, email_data: dict):
    # Call Telegram Bot API directly via httpx (bot doesn't need to be running)
    # On success: update notifications.status='sent'
    # On failure: update status='failed', retry
```

### How to verify Phase 2 is done

1. Visit `/api/v1/auth/microsoft/login` in a browser → redirects to Microsoft → authorize → returns to callback without error.
2. Check `mail_accounts` table — a new row should exist with encrypted tokens.
3. Trigger a manual sync: `docker compose exec worker celery -A app.workers.celery_app call app.workers.sync_tasks.sync_account --args='["<account_id>"]'`
4. Check `emails` table — rows should appear.
5. Check `mail_accounts.last_sync` — should be updated to a recent timestamp.

---

## Phase 3 — Telegram Bot

### What we're doing

The bot is the primary onboarding interface and notification delivery channel. By end of this phase: a user can DM the bot, get a connect link, authorize their email account, and start receiving Telegram notifications for new emails.

### Step 1 — Create the bot

1. Message `@BotFather` on Telegram.
2. `/newbot` → set name and username → copy the token.
3. Paste as `TELEGRAM_BOT_TOKEN` in `.env`.
4. Set bot commands via BotFather:
```
start - Register and get started
connect - Connect an email account
accounts - View connected accounts
disconnect - Remove an account
settings - Notification preferences
help - Help and documentation
```

### Step 2 — Implement handlers

All handlers live in `bot/handlers/`. The bot runs with aiogram 3.x using long polling in development and webhooks in production.

**`/start` handler (`bot/handlers/start.py`)**

When a user sends `/start`:
1. Extract `message.from_user.id` (Telegram ID).
2. POST to `backend` API: `POST /api/v1/users/register` with `telegram_id`.
3. Backend creates a `User` row if it doesn't exist.
4. Bot replies with a welcome message and inline keyboard showing `Connect Account` and `Help` buttons.

```
👋 Welcome to EmailAgg!

I'll notify you instantly when new emails arrive in your connected inboxes.

Use /connect to add your first account.
```

**`/connect` handler (`bot/handlers/connect.py`)**

1. Bot sends a message with two inline keyboard buttons: `Connect Outlook` and `Connect Gmail`.
2. Each button is a URL button pointing to:
   - `https://yourdomain.com/api/v1/auth/microsoft/login?telegram_id={user_id}`
   - `https://yourdomain.com/api/v1/auth/google/login?telegram_id={user_id}`
3. User taps the button, goes through OAuth in browser, backend stores tokens, user returns to Telegram.
4. After successful OAuth, backend calls the bot's API to send a confirmation: `✅ Outlook account [email] connected!`

> The `telegram_id` is passed as a query param through the OAuth flow (stored in the OAuth `state` parameter) so the backend knows which user to link the account to after the callback.

**`/accounts` handler (`bot/handlers/accounts.py`)**

1. GET `/api/v1/accounts?telegram_id={user_id}` from backend.
2. Format and display each account with status indicator:
```
📧 Your Connected Accounts

1. john@outlook.com  ✅ Active  (last sync: 2 min ago)
2. john@gmail.com    ✅ Active  (last sync: 5 min ago)

/connect to add more · /disconnect to remove
```

**`/help` handler** — static text with command list and link to dashboard.

**`/settings` handler** — future: notification frequency, filters, quiet hours.

### Step 3 — Notification message format

When `send_telegram_notification` task runs, it calls the Telegram Bot API directly using `httpx` (no aiogram needed in workers):

```python
async with httpx.AsyncClient() as client:
    await client.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": user_telegram_id,
            "parse_mode": "HTML",
            "text": (
                "📩 <b>New Email</b>\n\n"
                f"<b>From:</b> {from_name} &lt;{from_email}&gt;\n"
                f"<b>Subject:</b> {subject}\n"
                f"<b>Mailbox:</b> {mailbox_email}\n\n"
                f"<i>{snippet}</i>"
            ),
            "reply_markup": {
                "inline_keyboard": [[
                    {"text": "Open Dashboard", "url": f"{FRONTEND_URL}/emails/{email_id}"}
                ]]
            }
        }
    )
```

### Step 4 — Webhook vs polling

In development, polling is fine (the `dp.start_polling(bot)` call in `bot/main.py`).

In production, use webhooks — much more efficient:
```bash
# Register webhook with Telegram
curl -X POST "https://api.telegram.org/bot{TOKEN}/setWebhook" \
  -d "url=https://yourdomain.com/bot/webhook"
```

Add a webhook endpoint in `backend/app/api/routes/webhooks.py` that receives Telegram updates and processes them via aiogram's dispatcher.

### How to verify Phase 3 is done

1. DM the bot `/start` → get welcome message.
2. `/connect` → tap `Connect Outlook` → complete OAuth in browser → receive `✅ Connected` message in bot.
3. Send yourself an email to the connected account.
4. Within `SYNC_POLL_INTERVAL` seconds (default 300s, lower it to 30s for testing), receive a Telegram notification.
5. `/accounts` → see the account listed with status `Active`.

---

## Phase 4 — Web Dashboard

### What we're doing

A Next.js frontend that gives users a proper UI for account management and email browsing. The Telegram bot handles onboarding and notifications; the dashboard handles everything that needs a real screen.

### Tech stack

- **Next.js 14** with App Router
- **TypeScript**
- **Tailwind CSS** for styling
- **shadcn/ui** for components
- **SWR** for data fetching and caching
- **next-auth** for session management (JWT stored in cookie, backed by our API)

### Step 1 — Project setup

```bash
cd frontend
npx create-next-app@latest . --typescript --tailwind --app --src-dir
npx shadcn-ui@latest init
```

Configure `next.config.js` to proxy `/api/` requests to the FastAPI backend (avoids CORS issues in development).

### Step 2 — Pages and routes

```
/                   → Landing page (connect via Telegram CTA)
/dashboard          → Main view: account overview + recent emails
/dashboard/accounts → Manage connected accounts
/dashboard/accounts/connect → OAuth connect flow initiation
/dashboard/emails   → Full email list with filtering
/dashboard/settings → Notification preferences, plan info
/admin              → Admin panel (restricted to is_admin=True users)
/admin/users        → User list, account counts
/admin/workers      → Celery worker status, queue sizes
```

### Step 3 — Key components to build

**AccountCard** — shows provider icon, email address, sync status, last sync time, and a disconnect button.

**EmailList** — paginated table of emails: from, subject, received date, mailbox indicator. Filter by account. Click to see snippet in a modal.

**SyncStatusBadge** — `active` (green) / `syncing` (blue spinner) / `error` (red with tooltip showing error message) / `disconnected` (grey).

**ConnectButton** — opens the OAuth URL in the same tab. After redirect back, show success state.

**NotificationSettings** — toggle per-account notifications, set quiet hours (future Phase 5 feature, but build the UI shell now).

### Step 4 — API integration

All API calls go through a typed client in `frontend/src/lib/api.ts`. Never call the backend directly from components — always through this client. This makes it easy to swap URLs and handle auth errors globally.

The backend needs a few new endpoints to support the dashboard:

```
GET  /api/v1/users/me                      → current user info
GET  /api/v1/accounts                      → list user's mail accounts
DELETE /api/v1/accounts/{id}               → disconnect account
GET  /api/v1/emails?account_id=&page=&limit= → paginated email list
GET  /api/v1/emails/{id}                   → single email detail
```

Add these to the corresponding route files in `backend/app/api/routes/`.

### Step 5 — Admin panel

The admin panel is only accessible to users where `is_admin=True`.

Admin-specific backend endpoints:
```
GET /api/v1/admin/users        → all users with account counts
GET /api/v1/admin/stats        → worker count, queue sizes (from Redis)
GET /api/v1/admin/accounts     → all mail accounts across all users
PATCH /api/v1/admin/users/{id} → update plan, deactivate
```

For worker/queue stats, query Redis directly:
```python
from celery.app.control import Inspect
i = Inspect(app=celery_app)
stats = i.stats()      # worker stats
active = i.active()    # currently running tasks
```

### How to verify Phase 4 is done

1. Navigate to `http://localhost:3000` → landing page loads.
2. Log in (Telegram deeplink or OAuth redirect) → `/dashboard` shows connected accounts.
3. Click disconnect on an account → account disappears, DB row updated to `disconnected`.
4. Email list shows emails fetched by the sync worker, filterable by account.
5. Admin user can visit `/admin` and see all users and worker status.

---

## Phase 5 — Billing + Production Hardening

### What we're doing

Making the product ready for real users: subscription billing, monitoring, proper secrets management, and a production deployment checklist.

### Step 1 — Razorpay integration

1. Create a Razorpay account at [razorpay.com](https://razorpay.com), get API keys.
2. Add to `.env`: `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`.
3. Install: `pip install razorpay`.

**Backend changes:**

Write `backend/app/services/billing_service.py`:
```
POST /api/v1/billing/create-subscription   → create Razorpay subscription for chosen plan
POST /api/v1/billing/webhook               → Razorpay webhook for payment events
GET  /api/v1/billing/status                → current plan and next billing date
POST /api/v1/billing/cancel                → cancel subscription
```

When a `subscription.charged` webhook fires from Razorpay, update `users.plan` accordingly. When `subscription.cancelled` or `payment.failed`, downgrade to free.

**Plan enforcement:**

In the account connect endpoint, check:
```python
current_count = await get_account_count(user_id)
if current_count >= user.max_accounts:
    raise HTTPException(403, "Account limit reached for your plan. Upgrade to connect more.")
```

**Frontend changes:**

Add a `/dashboard/billing` page with:
- Current plan badge
- Upgrade/downgrade buttons (open Razorpay checkout)
- Next billing date
- Cancel subscription option

### Step 2 — Monitoring (Grafana + Prometheus + Loki)

Add to `docker-compose.yml`:

```yaml
prometheus:
  image: prom/prometheus:latest
  volumes:
    - ./infra/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml

grafana:
  image: grafana/grafana:latest
  environment:
    GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}

loki:
  image: grafana/loki:latest

promtail:
  image: grafana/promtail:latest
  volumes:
    - /var/log:/var/log
```

Expose Prometheus metrics from FastAPI using `prometheus-fastapi-instrumentator`:
```python
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)
```

Add custom metrics for:
- `emailagg_emails_synced_total` — counter per provider
- `emailagg_sync_errors_total` — counter per error type
- `emailagg_notification_latency_seconds` — histogram (time from email received to Telegram sent)
- `emailagg_active_accounts` — gauge

Import the provided Grafana dashboard JSON or build panels for:
- Emails synced per hour (by provider)
- Worker task success/failure rate
- Celery queue depth over time
- API request rate and latency (p50, p95, p99)
- Notification delivery success rate

### Step 3 — Structured logging

Replace `print`/`logging.info` throughout the codebase with `structlog`:

```python
import structlog
logger = structlog.get_logger()

logger.info("sync_complete", account_id=account_id, emails_fetched=count, duration_ms=elapsed)
logger.error("sync_failed", account_id=account_id, error=str(exc), provider=account.provider)
```

Structured logs (JSON format) are ingested by Promtail and stored in Loki, queryable in Grafana.

### Step 4 — Production deployment checklist

**Secrets**
- [ ] All secrets rotated from dev values
- [ ] `.env` not committed to git (check `.gitignore`)
- [ ] Fernet key backed up securely (if lost, all tokens must be re-collected)
- [ ] POSTGRES_PASSWORD is strong (32+ char random)

**Nginx**
- [ ] Replace `yourdomain.com` in `infra/nginx/conf.d/default.conf`
- [ ] Run Certbot to get Let's Encrypt certificate:
  ```bash
  docker run --rm -v certbot_www:/var/www/certbot -v certbot_certs:/etc/letsencrypt \
    certbot/certbot certonly --webroot -w /var/www/certbot -d yourdomain.com
  ```
- [ ] Set up auto-renewal cron: `0 0 * * * certbot renew`

**Database**
- [ ] Set up daily `pg_dump` to object storage (e.g. Backblaze B2 or S3)
- [ ] Test restore from backup before going live

**Workers**
- [ ] Celery concurrency tuned to available CPU (4 workers on 4-vCPU VPS)
- [ ] `task_acks_late=True` confirmed (already set in scaffold)
- [ ] Flower accessible only on internal network or behind HTTP auth

**Microsoft Graph**
- [ ] Webhook subscription renewal beat task running
- [ ] Verify webhook endpoint is reachable from Microsoft's servers

**Rate limiting**
- [ ] `RATE_LIMIT_PER_MINUTE` set to a sensible value per plan
- [ ] Redis-based rate limit keys so limits persist across API restarts

**App settings**
- [ ] `APP_ENV=production` in `.env` (disables `/api/docs`)
- [ ] `DEBUG=False` / logging level set to `WARNING` or `ERROR` in production

### Step 5 — VPS setup (minimum spec from PRD)

Recommended for initial production deployment:
- 4 vCPU, 8GB RAM, 100GB SSD
- Ubuntu 22.04 LTS
- Docker + Docker Compose v2

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Clone repo, fill .env, start
git clone https://github.com/your-org/emailagg
cd emailagg
cp .env.example .env
# ... fill in .env ...
docker compose up -d
docker compose run --rm backend alembic upgrade head
```

### How to verify Phase 5 is done

1. Navigate to `/dashboard/billing` → current plan shown, upgrade button opens Razorpay checkout.
2. Upgrade from free to pro → `users.plan` updates to `pro` in DB → account limit raised.
3. Grafana at `https://yourdomain.com/grafana` → dashboard shows live email sync metrics.
4. Simulate a sync failure → error appears in Grafana + Loki within 60 seconds.
5. `https://yourdomain.com` (HTTP) → 301 redirect to HTTPS.
6. SSL certificate is valid (Let's Encrypt), no browser warnings.

---

## Summary — What "done" looks like for the whole product

| Capability | Phase |
|---|---|
| Docker environment running locally | 1 |
| Database tables created and migrated | 1 |
| FastAPI health check passing | 1 |
| Microsoft OAuth flow end-to-end | 2 |
| Gmail OAuth flow end-to-end | 2 |
| Emails appearing in DB from real inboxes | 2 |
| Token refresh working without manual intervention | 2 |
| Telegram bot `/start` and `/connect` working | 3 |
| Telegram notification delivered for new email | 3 |
| Web dashboard showing connected accounts | 4 |
| Email list browsable in dashboard | 4 |
| Admin panel showing users and worker status | 4 |
| Razorpay subscription billing working | 5 |
| Plan limits enforced on account connect | 5 |
| Grafana dashboards live in production | 5 |
| HTTPS, backups, and secrets properly managed | 5 |

---

## Key decisions to revisit as the product grows

**Webhook-first, polling as fallback.** Start with polling for MVP (simpler), migrate accounts to webhooks in Phase 2 after the basic sync is proven stable.

**IMAP in Phase 2, not Phase 1.** IMAP adds complexity. Get Microsoft + Gmail working first, then add IMAP for the long tail.

**Telegram Mini App (future).** The PRD mentions this as a future option for richer in-Telegram UI. Don't build it now. The web dashboard covers all MVP needs.

**Stripe migration (future).** Razorpay for Indian market initially. When international users grow, add Stripe as a second billing provider — the `billing_service.py` abstraction will make this easier.

**AI features (Phase 6+).** Email summarization, priority classification, smart replies — none of these are in scope until the core pipeline (Phases 1-5) is stable and has real users.
