# EmailAgg Repository Commit History

This document contains a record of recent commits for the EmailAgg repository, documenting the latest features, bug fixes, and infrastructure changes.

## Recent Commits

*   **`537e294`** - Blackx16, Sat Jul 4 18:14:54 2026 +0530
    *fix(worker): offload email forwarding to async celery queue*
*   **`346c8cf`** - Blackx16, Sat Jul 4 05:18:25 2026 +0530
    *feat(infra): setup log backup script config*
*   **`de5cbff`** - Blackx16, Sat Jul 4 05:17:46 2026 +0530
    *feat: complete mission control dashboard and event telemetry*
*   **`42b31c4`** - Blackx16, Sat Jul 4 01:47:35 2026 +0530
    *feat(infra): Add Google Drive log backup script for paid tier*
*   **`f87b504`** - Blackx16, Sat Jul 4 01:46:41 2026 +0530
    *chore: Apply security hardening (Auth, Internal APIs, Nginx proxy blocking)*
*   **`450a8e6`** - Blackx16, Thu Jul 2 18:39:44 2026 +0530
    *feat: Add interval CPU and Storage usage graphs to Mission Control Dashboard*
*   **`4b5a1e7`** - Blackx16, Thu Jun 18 15:12:23 2026 +0530
    *Default forward_enabled to True on new connections and reactivations, and restrict sync to emails received after connection time*
*   **`5156284`** - Blackx16, Thu Jun 18 14:56:31 2026 +0530
    *Fix Mission Control subfolder routing, pin requests for docker-py, and remove debug logging*
*   **`f18ca91`** - Blackx16, Thu Jun 18 14:48:54 2026 +0530
    *Add debug print statement to basic_auth_middleware*
*   **`2a02467`** - Blackx16, Thu Jun 18 14:47:02 2026 +0530
    *Add --root-path /control to Uvicorn command*
*   **`cf76369`** - Blackx16, Thu Jun 18 14:39:22 2026 +0530
    *Deploy Mission Control dashboard and fix Telegram accounts and ID mismatch*
*   **`7a41c60`** - Blackx16, Sat Jun 13 04:24:54 2026 +0530
    *fix: add url_prefix to Flower and remove trailing slash from Nginx proxy pass to load styles correctly*
*   **`725d69b`** - Blackx16, Sat Jun 13 04:18:28 2026 +0530
    *deploy: configure SSL bind mount and Nginx SSL redirect for teleswift domain*
*   **`ad17c23`** - Blackx16, Sat Jun 13 01:06:38 2026 +0530
    *feat: rich HTML email forwarding, in-memory IMAP parser, and GitHub Pages landing page*
*   **`0af4ade`** - Blackx16, Thu Jun 11 18:30:58 2026 +0530
    *feat: implement API-based forwarding via Google and Microsoft Graph APIs*
*   **`bbbbbc0`** - Blackx16, Thu Jun 11 17:32:29 2026 +0530
    *fix: add 10-second timeout to SMTP forwarding client*
*   **`8c7802d`** - Blackx16, Thu Jun 11 16:36:47 2026 +0530
    *fix: resolve sync failures by forcing IPv4 transport, handling Celery connection pool mismatches, and restarting scheduler*
*   **`54cff9d`** - Blackx16, Thu Jun 11 06:20:27 2026 +0530
    *Fix 'Load failed' by removing frontend volume bind-mount and adding .dockerignore*
*   **`d0d52d0`** - Blackx16, Thu Jun 11 05:03:06 2026 +0530
    *feat: 4-queue Celery, notification throttle, PII audit, UI fixes*
*   **`d259b96`** - Blackx16, Wed Jun 10 13:31:26 2026 +0530
    *Implement Email Rules, SMTP Forwarding Engine, and Bot Command*
*   **`c33f8d4`** - Blackx16, Wed Jun 10 11:50:05 2026 +0530
    *feat(phase-a): implement mailbox preferences toggles, login rate limits, and unique email constraints*
*   **`4cf1dc4`** - Blackx16, Wed Jun 10 00:20:29 2026 +0530
    *Update docker-compose with external network for db and redis*
*   **`48c6037`** - Blackx16, Mon Jun 8 03:43:14 2026 +0530
    *Update free tier plan limit to 500 and fix backend health check hostname*
*   **`339a80e`** - Blackx16, Sat Jun 6 17:11:31 2026 +0530
    *fix: correct HMAC argument order for Telegram WebApp signature (key=WebAppData, data=bot_token)*
*   **`aec23e4`** - Blackx16, Sat Jun 6 03:16:39 2026 +0530
    *feat: production readiness overhaul*
*   **`f67753e`** - Blackx16, Fri Jun 5 19:55:13 2026 +0530
    *Initial commit*
