# DECISIONS

| ID | Date | Decision | Rationale | Alternatives Considered |
|---|---|---|---|---|
| D001 | 2026-10-12 | Use SQLite locally and PostgreSQL for Docker/prod | Minimal dev overhead, full compliance with spec | Run PG only |
| D002 | 2026-10-12 | Redirect out-of-range pagination to the last valid page | Prevents dead ends for students accessing stale pagination links | Return 404 |
