## 2024-07-10 - Preventing O(N) memory load in IMAP Sync
**Learning:** Loading all message IDs for an account into memory (`existing_result.scalars().all()`) to deduplicate a small batch of incoming IMAP emails causes a massive memory leak (O(N) memory, where N is all emails).
**Action:** Extract headers for the current batch first, then perform a single bulk query with an `IN` clause to fetch only relevant existing message IDs, reducing memory footprint to O(1) regarding total account size.
## 2024-07-10 - Preventing N+1-like memory inflation using func.count()
**Learning:** Loading all related ORM objects into memory to calculate counts (e.g., `sum(1 for a in accounts)`) or find a single record is a performance anti-pattern that leads to O(N) memory inflation as user data grows.
**Action:** Always delegate counting and existence checks to the database using targeted `select` queries and `func.count()`.
## 2026-06-25 - IMAP Sync O(N) Memory Leak Prevention
**Learning:** Found a major performance bottleneck where `IMAPSyncService` loaded ALL existing database emails for an account (`len(existing_result.scalars().all())`) into memory just to prevent an N+1 deduplication issue.
**Action:** When deduplicating large collections, use a two-pass chunked approach: first gather incoming IDs, then perform bounded `IN` queries to fetch only the existing IDs relevant to the current batch. This stops memory utilization from growing O(N) over time.
