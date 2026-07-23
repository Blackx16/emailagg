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
The production deployment is hosted on a VPS.
- **Host / IP Address:** `152.228.227.51`
- **SSH User:** `root`
- **SSH Port:** `20009`

To connect via SSH:
```bash
ssh -o StrictHostKeyChecking=no -p 20009 root@152.228.227.51
```
The repository is cloned to `/root/emailagg` on the remote host, and is orchestrated using `docker-compose.yml`.

- **Direct VPS Editing**: Whenever instructed to make code fixes or run commands, do it directly on the production VPS (`root@152.228.227.51` via port `20009`) in the `/root/emailagg` directory, and NEVER in the local workspace unless specifically told to do so.
- **Safe Docker Restarts**: When restarting or recreating any backend containers (e.g., via `docker compose up -d --force-recreate ...`) on the VPS, ALWAYS recreate or restart the `nginx` container alongside them (and reload nginx). If Nginx is not refreshed, it will cache stale internal Docker IPs, resulting in a 502 Bad Gateway error for the live site.
- **VPS Deployment Synchrony**: When deploying code fixes to the VPS, updating local files is not sufficient. You must explicitly transfer the changes to the VPS (via git push/pull or SCP) and then explicitly rebuild the affected containers using `docker compose up -d --build --force-recreate <service> nginx`, followed by `docker compose restart nginx`. Be mindful that Docker builds may cache old code if the context isn't correctly synchronized.

## Development & Debugging Gotchas

- **Aiogram CallbackQueries & User IDs**: When a function is triggered via an inline button (`CallbackQuery`), never rely on `message.from_user.id` or `message.chat.id` if the message is passed from the callback (`callback.message`). The `message` belongs to the Bot, and you will accidentally query the Bot's ID instead of the user's. **Always explicitly pass `callback.from_user.id`** from the callback handler to any underlying functions.
- **Next.js & Nginx `/api/` Routing Conflict**: Because Next.js App Router uses `/api/` for its own server-side routes, configuring Nginx to blindly proxy `location /api/` to the backend will break Next.js API routes (resulting in 404s from the backend). Always bind the Nginx backend proxy to a strictly versioned path (e.g., `location /api/v1/`) so Next.js routes fall through correctly to the frontend container.
- **Telegram WebApp Initialization Race Condition**: When building Next.js Telegram WebApps, injecting the SDK via `<Script src="https://telegram.org/js/telegram-web-app.js" />` can cause race conditions on slow mobile connections. `window.Telegram` might be `undefined` when the initial React components mount. Always wrap `window.Telegram.WebApp.initData` checks in a retry/polling loop (e.g., 2 seconds) instead of synchronously falling back to browser-mode if it's missing on the first render.
- **API Paths and Nginx Proxy**: The frontend connects to the FastAPI backend through Nginx. Frontend `fetch` requests must use the strictly versioned path (e.g. `fetch('/api/v1/emails')`) which Nginx proxies to the backend. The backend router endpoints must perfectly align with the frontend fetch paths. **Avoid rogue path segments** (e.g., mistakenly using `/api/v1/mail/emails` when the backend only defines `/api/v1/emails`).
- **Pagination Response Structures**: When consuming backend paginated endpoints (like `/api/v1/emails`), note that the FastAPI backend returns `data.emails` and `data.total_pages`, not `data.items` or `data.pages`. Always verify the expected Pydantic schema or backend dictionary return structure when mapping data to Next.js states.
- **CSS `transform` & Fixed Overlays**: Avoid placing `position: fixed` modals, popovers, or bottom-sheets inside parent containers that use CSS `transform` (e.g. horizontal slide tab wrappers using `transform: translateX(...)`). In standard CSS, `transform` creates a new containing block, causing `fixed` children to align relative to the transformed element instead of the viewport. Use inline `absolute` positioning or React Portals (`createPortal`) to `document.body`.
- **Dynamic Tab Height Isolation**: In slide-transitioned multi-tab layouts (e.g., `Inbox`, `Mailboxes`, `Rules`), avoid full-width `flex w-[300%]` containers that force the document height to match the tallest tab. Use a per-tab `relative`/`absolute` wrapper (`activeTabIndex === i ? "relative" : "absolute top-0 left-0 pointer-events-none"`). This keeps document height strictly equal to the active tab's content, eliminating empty trailing scroll space.
- **Local Docker Testing Environment**: Maintain `docker-compose.local.yml` (listed in `.gitignore`) for local pre-deployment testing. Use a dedicated test Telegram Bot token in `.env` while syncing production secrets from the VPS (`152.228.227.51`) in read-only mode. Never write or push directly from local to VPS without testing locally first.
