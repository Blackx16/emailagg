# EmailAgg — Unified Email Aggregation SaaS

Aggregates multiple Outlook/Gmail/IMAP inboxes, syncs via OAuth APIs, and pushes Telegram notifications. No forwarding rules. No stored passwords.

---

## Project layout

```
emailagg/
├── backend/                # FastAPI app + Celery workers
│   ├── app/
│   │   ├── api/routes/     # FastAPI route handlers
│   │   ├── core/           # Config, encryption, rate-limiting
│   │   ├── db/             # SQLAlchemy models + session
│   │   ├── services/       # OAuth + sync service classes (Phase 2)
│   │   ├── workers/        # Celery tasks
│   │   └── schemas/        # Pydantic request/response schemas
│   ├── alembic/            # DB migrations
│   └── requirements.txt
├── bot/                    # aiogram Telegram bot
│   └── handlers/           # /start /connect /accounts /help
├── frontend/               # Next.js dashboard (Phase 4)
├── infra/
│   └── nginx/              # Reverse proxy config
├── scripts/
│   └── generate_secrets.sh
├── docker-compose.yml
└── .env.example
```

---

## Quick start (local dev)

```bash
# 1. Clone and copy env
cp .env.example .env

# 2. Generate secrets
bash scripts/generate_secrets.sh   # copy output into .env

# 3. Fill in OAuth credentials in .env
#    (Microsoft Azure portal + Google Cloud Console)

# 4. Start core services
docker compose up db redis -d

# 5. Run migrations
docker compose run --rm backend alembic upgrade head

# 6. Start everything
docker compose up
```

API docs: http://localhost:8000/api/docs  
Celery monitor: http://localhost:5555

---

## Phases

| Phase | What |
|---|---|
| 1 | Core architecture (this scaffold) |
| 2 | OAuth + mail sync workers |
| 3 | Telegram bot integration |
| 4 | Web dashboard |
| 5 | Billing (Razorpay) + production hardening |

---

## Security notes

- OAuth tokens are encrypted at rest with Fernet before any DB write.
- Internal services (`db`, `redis`, `worker`, `beat`) are on a Docker `internal` network — no direct internet access.
- Nginx enforces HTTPS; HTTP redirects to HTTPS.
- Rate limiting via `slowapi` on all API routes.
- Never commit `.env`.
