# EmailAgg — Unified Email Aggregation & Forwarding SaaS

EmailAgg is a self-hosted, enterprise-grade Email Aggregation SaaS that compiles emails from multiple inboxes (Gmail, Microsoft Outlook, and custom IMAP accounts) and delivers instant notifications to a Telegram bot. 

It features direct API email forwarding, smart OTP extraction, and granular routing rule scoping.

🌐 **Live Project Landing Page:** [https://Blackx16.github.io/emailagg/](https://Blackx16.github.io/emailagg/)

---

## Key Features

*   **OAuth 2.0 Provider Send APIs:** Forwards matched emails directly from your own Gmail or Outlook address using official Google REST APIs (`POST /messages/send`) and Microsoft Graph APIs (`POST /me/sendMail`). No generic third-party SMTP relays or domain spoofing risks.
*   **In-Memory IMAP Sync:** Synced IMAP mailboxes fall back to the system-wide SMTP relay, utilizing optimized in-memory MIME parsing to forward HTML messages directly without extra API lookups.
*   **Smart OTP/Verification Code Parser:** Automatically parses and extracts numeric and alphanumeric verification codes using robust regex filters. OTP codes are pushed directly to Telegram notifications in a copyable monospace layout.
*   **Granular Rules Match Engine:** Filter and forward emails based on custom criteria (Subject contains, From exact email, From domain, and Body contains). Scope rules to a specific connected mailbox or globally across all active mailboxes.
*   **Security-First Cryptography:** No plain-text email passwords are stored. Google/Microsoft connections use secure OAuth tokens. Custom IMAP login credentials are encrypted at rest using Fernet AES-256 symmetric encryption.
*   **Redis Rate Limiting & Lock Deduplication:** Features hourly limits (max 50 notifications/forwards per user per hour) to protect IP reputation. Runs a distributed locking mechanism (`sync_lock:{account_id}`) in Redis to prevent Celery concurrency collisions.
*   **Internal Network Isolation:** PostgreSQL, Redis, Celery sync/notification/forwarding workers, and Celery Beat run on a decoupled internal Docker network with zero public ingress.

---

## Folder Architecture

```
emailagg/
├── backend/                  # FastAPI app + Celery workers
│   ├── app/
│   │   ├── api/routes/       # FastAPI REST endpoints
│   │   ├── core/             # Redis, Fernet encryption, security headers, rate-limiting
│   │   ├── db/               # SQLAlchemy models + DB sessions (NullPool for Celery workers)
│   │   ├── services/         # Sync workers, OAuth connectors, forwarding service
│   │   ├── workers/          # Celery task definitions
│   │   └── schemas/          # Pydantic validation schemas
│   ├── alembic/              # DB migrations (Alembic auto-migration wrapper)
│   └── requirements.txt
├── bot/                      # aiogram Telegram Bot handlers
│   └── handlers/             # Bot commands (/start, /connect, /rules, /settings, /disconnect)
├── frontend/                 # Next.js static production client (packaged via multi-stage Docker build)
├── infra/
│   └── nginx/                # Reverse proxy config (Nginx SSL + Security headers)
├── docs/                     # Static landing page hosted on GitHub Pages
├── scripts/
│   └── generate_secrets.sh
├── docker-compose.yml
└── .env.example
```

---

## Telegram Bot Commands

*   `/start` — Registers a profile and prints setup instructions.
*   `/connect` — Generates a secure OAuth deep-link to connect a Gmail or Microsoft Outlook mailbox.
*   `/rules` — Lists active filtering/forwarding rules and includes a direct link to open the rules dashboard.
*   `/settings` — Displays subscription plan status, usage capacity indicator (`▓▓░░`), and current notification limits.
*   `/disconnect` — Prompts an inline list of connected mailboxes with options to revoke OAuth keys and disconnect.

---

## Quick Start (Local Development)

### 1. Configure the Environment
Copy the example environment file and run the secret key generator script:
```bash
cp .env.example .env
bash scripts/generate_secrets.sh
```
Fill in the generated keys along with your Google Cloud Console and Microsoft Azure App Registration Client credentials in the `.env` file.

### 2. Launch Core Services
Start Postgres and Redis containers:
```bash
docker compose up db redis -d
```

### 3. Run Database Migrations
Run Alembic migrations to build the tables:
```bash
docker compose run --rm backend alembic upgrade head
```

### 4. Boot Up the Platform
Start the FastAPI server, Next.js client, Telegram bot, and all Celery worker processes:
```bash
docker compose up --build
```
*   **FastAPI REST Documentation:** [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
*   **Flower Celery Monitor:** [http://localhost:5555](http://localhost:5555)
*   **Dashboard Client:** [http://localhost:3000](http://localhost:3000)

---

## Automated Verification
To validate database unique constraints, rate-limiters, rule evaluation, OTP extraction, and mock API sending routes, run the test suites inside the backend container:
```bash
docker compose exec backend python -m app.test_integration
docker compose exec backend python -m app.test_rules_and_limiter
```
