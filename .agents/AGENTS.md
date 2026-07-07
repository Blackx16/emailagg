# Project Rules

- **Git Syncing**: Any changes made to the codebase should be automatically synced (committed and pushed) to all relevant tracking branches (e.g. `main` and `paid`), except when explicitly instructed by the user to NOT sync with a specific branch.

# EmailAgg Project

EmailAgg is a scalable email aggregation SaaS platform that centralizes emails from multiple providers (Google, Microsoft, and custom IMAP). It features a robust Python/FastAPI backend, Celery workers for background syncing and notifications, a PostgreSQL database for state, and Redis for caching and message broking. The application also includes a Telegram bot interface for user interactions.

## Architecture Highlights
- **Backend:** FastAPI, SQLAlchemy (asyncpg)
- **Background Workers:** Celery (Sync, Notifications, Forwarding, Maintenance)
- **Databases:** PostgreSQL (primary data), Redis (Celery broker, caching, rate limiting)
- **Deployment:** Docker Compose on a single-node VPS

## Server Connection Details
The production deployment is hosted on an Azure VPS.
- **Host / IP Address:** `4.218.8.104`
- **SSH User:** `azureuser`
- **SSH Key:** `emailagg-vm_key.pem` (located in the project root directory)

To connect via SSH:
```bash
chmod 400 emailagg-vm_key.pem
ssh -i emailagg-vm_key.pem azureuser@4.218.8.104
```
The repository is cloned to `~/emailagg` on the remote host, and is orchestrated using `docker-compose.yml`.

- **Direct VPS Editing**: Whenever instructed to make code fixes or run commands, do it directly on the production Azure VPS (`azureuser@4.218.8.104`) in the `~/emailagg` directory, and NEVER in the local workspace unless specifically told to do so.
