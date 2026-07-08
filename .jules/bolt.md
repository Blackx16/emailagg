## 2024-03-24 - [Avoid `len(res.scalars().all())` for Database Counting]
**Learning:** Loading full SQLAlchemy ORM objects into memory just to count them (`len(res.scalars().all())`) is a major performance bottleneck (effectively an N+1 issue for memory usage). The database is far faster at counting.
**Action:** Always use SQLAlchemy's `func.count()` (e.g., `select(func.count()).select_from(Model)`) to count database records directly inside the query execution.
