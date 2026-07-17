## 2024-07-10 - Preventing O(N) memory load in IMAP Sync
**Learning:** Loading all message IDs for an account into memory (`existing_result.scalars().all()`) to deduplicate a small batch of incoming IMAP emails causes a massive memory leak (O(N) memory, where N is all emails).
**Action:** Extract headers for the current batch first, then perform a single bulk query with an `IN` clause to fetch only relevant existing message IDs, reducing memory footprint to O(1) regarding total account size.
## 2024-07-10 - Preventing N+1-like memory inflation using func.count()
**Learning:** Loading all related ORM objects into memory to calculate counts (e.g., `sum(1 for a in accounts)`) or find a single record is a performance anti-pattern that leads to O(N) memory inflation as user data grows.
**Action:** Always delegate counting and existence checks to the database using targeted `select` queries and `func.count()`.

## 2024-05-24 - O(N) Memory Leak in IMAP Sync
**Learning:** Pre-fetching all existing database records to prevent N+1 query problems (e.g., `existing_result = await self.db.execute(select(Email.message_id).where(Email.mail_account_id == self.account.id)); set(existing_result.scalars().all())`) creates an O(N) memory leak that crashes worker processes as mailboxes grow.
**Action:** Always fetch the necessary external identifiers in a first pass, then perform a chunked or bounded `IN` query against the database (e.g., `Email.message_id.in_(fetched_ids)`) to retrieve only the relevant subset of existing records before processing.
