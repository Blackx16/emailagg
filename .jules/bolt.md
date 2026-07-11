## 2026-07-11 - Database In-Memory Filtering Bottleneck
**Learning:** Loading full ORM objects into memory to count them using `sum(1 for a in ...)` or filtering them in-memory using generators creates an N+1 equivalent memory/CPU bottleneck when scaling accounts. The database should handle counting.
**Action:** Always use `select(func.count())` for counting rows and filter precisely via `where(...)` clauses instead of iterating over `res.scalars().all()`.
