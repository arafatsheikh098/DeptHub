# DECISIONS

| ID | Date | Decision | Rationale | Alternatives Considered |
|---|---|---|---|---|
| D001 | 2026-10-12 | Use SQLite locally and PostgreSQL for Docker/prod | Minimal dev overhead, full compliance with spec | Run PG only |
| D002 | 2026-10-12 | Redirect out-of-range pagination to the last valid page | Prevents dead ends for students accessing stale pagination links | Return 404 |
| D003 | 2026-10-12 | Block deletion of batches with existing routine slots or exams | Prevents accidental cascading loss of departmental routine and exam data | Cascade delete |
| D004 | 2026-10-12 | Use data-auto-submit in app.js instead of inline onchange | Strict CSP bans 'unsafe-inline' scripts; provides auto-submit without violating CSP | Allow unsafe-inline in script-src |
