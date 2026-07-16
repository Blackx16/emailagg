## 2024-07-10 - Preventing O(N) memory load in IMAP Sync
**Learning:** Loading all message IDs for an account into memory (`existing_result.scalars().all()`) to deduplicate a small batch of incoming IMAP emails causes a massive memory leak (O(N) memory, where N is all emails).
**Action:** Extract headers for the current batch first, then perform a single bulk query with an `IN` clause to fetch only relevant existing message IDs, reducing memory footprint to O(1) regarding total account size.
## 2024-07-10 - Preventing N+1-like memory inflation using func.count()
**Learning:** Loading all related ORM objects into memory to calculate counts (e.g., `sum(1 for a in accounts)`) or find a single record is a performance anti-pattern that leads to O(N) memory inflation as user data grows.
**Action:** Always delegate counting and existence checks to the database using targeted `select` queries and `func.count()`.

## 2026-07-16 - IMAP Sync O(N) Memory Leak Prevention
**Learning:** During data synchronization processes, such as deduplicating synced IMAP emails, eagerly loading all existing database records (`select(Email.message_id).where(...)` -> `result.scalars().all()`) creates a significant O(N) memory leak that crashes the sync worker as the table grows.
**Action:** When performing existence checks against large tables during syncing, always employ a first-pass loop to collect the necessary identifiers, followed by a bounded chunked `IN` query to fetch only the existing overlap, rather than pulling the entire historical dataset into memory.
