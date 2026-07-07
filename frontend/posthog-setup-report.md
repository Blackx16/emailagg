# PostHog post-wizard report

The wizard has completed a deep integration of PostHog analytics into EmailAgg, a Telegram WebApp email aggregation dashboard. The integration covers client-side initialization via `instrumentation-client.ts`, user identification on login and session restore, 14 tracked events across authentication and core product flows, exception capture at error boundaries, and a reverse proxy configuration to avoid ad-blocker interference.

## Files modified

| File | Change |
|---|---|
| `instrumentation-client.ts` (new) | Client-side PostHog initialization with reverse proxy and exception autocapture |
| `next.config.ts` | Added PostHog reverse proxy rewrites and `skipTrailingSlashRedirect` |
| `.env.local` (new) | `NEXT_PUBLIC_POSTHOG_PROJECT_TOKEN` and `NEXT_PUBLIC_POSTHOG_HOST` |
| `src/context/AuthContext.tsx` | `posthog.identify()` on Telegram login and localStorage restore; `posthog.reset()` + capture on logout |
| `src/app/page.tsx` | 14 capture calls across all user-facing flows |

## Tracked events

| Event name | Description | File |
|---|---|---|
| `telegram_login_completed` | Fires when a user successfully authenticates via Telegram WebApp initData. | `src/context/AuthContext.tsx` |
| `user_logged_out` | Fires when the user taps the logout button to end their session. | `src/context/AuthContext.tsx` |
| `oauth_connect_initiated` | Fires when the user clicks to start a Microsoft or Google OAuth mailbox connection. | `src/app/page.tsx` |
| `imap_connect_form_opened` | Fires when the user opens the custom IMAP SSL connection dialog. | `src/app/page.tsx` |
| `mailbox_connected` | Fires when a new IMAP mailbox is successfully connected. | `src/app/page.tsx` |
| `mailbox_disconnected` | Fires when a user disconnects a connected mailbox account. | `src/app/page.tsx` |
| `account_preference_updated` | Fires when the user toggles a per-account preference (dashboard delivery, Telegram alerts, or forwarding). | `src/app/page.tsx` |
| `notification_limit_saved` | Fires when the user saves a custom Telegram notification limit per hour. | `src/app/page.tsx` |
| `email_opened` | Fires when the user clicks an email item to view its full details. | `src/app/page.tsx` |
| `inbox_searched` | Fires when the user submits a search query in the inbox search bar. | `src/app/page.tsx` |
| `inbox_filter_applied` | Fires when the user changes a filter (read status, provider, or mailbox) in the inbox. | `src/app/page.tsx` |
| `forwarding_rule_created` | Fires when the user successfully creates a new email forwarding rule. | `src/app/page.tsx` |
| `forwarding_rule_deleted` | Fires when the user confirms deletion of a forwarding rule. | `src/app/page.tsx` |
| `forwarding_rule_toggled` | Fires when the user enables or disables an existing forwarding rule. | `src/app/page.tsx` |

## Next steps

We've built some insights and a dashboard for you to keep an eye on user behavior, based on the events we just instrumented:

- [Analytics basics (wizard) dashboard](https://us.posthog.com/project/499400/dashboard/1806821)
- [Daily Logins (wizard)](https://us.posthog.com/project/499400/insights/d8dVbAGh)
- [Mailbox Connection Funnel (wizard)](https://us.posthog.com/project/499400/insights/vXLpBGin)
- [Email Engagement (wizard)](https://us.posthog.com/project/499400/insights/TJwv79qK)
- [Forwarding Rule Activity (wizard)](https://us.posthog.com/project/499400/insights/8c5CV9a7)
- [Mailbox Connections Over Time (wizard)](https://us.posthog.com/project/499400/insights/UsS2J1NI)

## Verify before merging

- [ ] Run a full production build (`npm run build`) and fix any lint or type errors introduced by the generated code.
- [ ] Run the test suite (`npm test`) — call sites that were rewritten or instrumented may need updated mocks or fixtures.
- [ ] Add `NEXT_PUBLIC_POSTHOG_PROJECT_TOKEN` and `NEXT_PUBLIC_POSTHOG_HOST` to `.env.example` and any deployment/bootstrap scripts so collaborators know what to set.
- [ ] Wire source-map upload (`posthog-cli sourcemap` or your bundler's upload step) into CI so production stack traces de-minify.
- [ ] Confirm the returning-visitor path also calls `identify` — the current implementation identifies on Telegram login and on localStorage restore; verify both paths work in your Telegram WebApp test environment.

### Agent skill

We've left an agent skill folder in your project at `.claude/skills/integration-nextjs-app-router/`. You can use this context for further agent development when using Claude Code. This will help ensure the model provides the most up-to-date approaches for integrating PostHog.
