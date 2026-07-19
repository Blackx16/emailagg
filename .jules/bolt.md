## 2024-07-10 - Preventing O(N) memory load in IMAP Sync
**Learning:** Loading all message IDs for an account into memory (`existing_result.scalars().all()`) to deduplicate a small batch of incoming IMAP emails causes a massive memory leak (O(N) memory, where N is all emails).
**Action:** Extract headers for the current batch first, then perform a single bulk query with an `IN` clause to fetch only relevant existing message IDs, reducing memory footprint to O(1) regarding total account size.
## 2024-07-10 - Preventing N+1-like memory inflation using func.count()
**Learning:** Loading all related ORM objects into memory to calculate counts (e.g., `sum(1 for a in accounts)`) or find a single record is a performance anti-pattern that leads to O(N) memory inflation as user data grows.
**Action:** Always delegate counting and existence checks to the database using targeted `select` queries and `func.count()`.
## 2024-07-19 - Avoid O(N) memory leak in IMAP sync deduplication
**Learning:** Loading all `message_id`s for a given account directly into memory (`set(existing_result.scalars().all())`) can cause O(N) memory usage, leading to significant memory consumption when dealing with a large volume of emails.
**Action:** When performing deduplication during syncing, use bounded query deduplication strategies. First fetch the set of potentially new `message_id`s, then run chunked `IN` queries (e.g., in chunks of 100) to fetch the intersection of existing emails.
