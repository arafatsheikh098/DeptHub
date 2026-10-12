# PLAN: DeptHub Implementation Plan

## M1: Foundation [COMPLETED]
### Scope & Deliverables
- Project configuration (`app/config.py`) using `pydantic-settings`, reading from environment with documented `.env.example`. Refuses default secret in production.
- Database session dependency and engine setup (`app/database.py`) supporting both SQLite and PostgreSQL.
- SQLModel models for all entities (`app/models/`): Admin User, Notice, Batch, Section, RoutineSlot, Exam, AuditLog, LoginAttempt.
- Alembic database migrations setup (`alembic/`, `alembic.ini`) with initial migration `001_initial.py`.
- Application factory (`app/main.py`) with `GET /health` endpoint verifying database connection.
- Base Jinja2 layout (`app/templates/base.html`) integrating vendored Pico.css.
- Deployment and developer tooling: `Dockerfile` (python:3.12-slim, non-root user, HEALTHCHECK), `docker-compose.yml` (app + postgres services, named volume), `Makefile`, GitHub Actions CI workflow (`.github/workflows/ci.yml`), `README.md` stub.
### Files Created
- `app/__init__.py`
- `app/config.py`
- `app/database.py`
- `app/models/__init__.py`
- `app/models/user.py`
- `app/models/notice.py`
- `app/models/batch.py`
- `app/models/routine.py`
- `app/models/exam.py`
- `app/models/audit.py`
- `app/models/rate_limit.py`
- `app/main.py`
- `app/templates/base.html`
- `app/static/css/pico.min.css`
- `app/static/css/pico.LICENSE.md`
- `alembic.ini`
- `alembic/env.py`
- `alembic/script.py.mako`
- `alembic/versions/001_initial.py`
- `Dockerfile`
- `docker-compose.yml`
- `Makefile`
- `.github/workflows/ci.yml`
- `.env.example`
- `.gitignore`
- `README.md`
### Tests Needed
- `tests/conftest.py`: SQLite and Postgres test fixtures.
- `tests/test_health.py`: Verifies `GET /health` returns 200 `{"status": "ok"}` and fails if DB is unreachable.
- `tests/test_migrations.py`: Verifies Alembic upgrade and downgrade on SQLite and PostgreSQL.

---

## M2: Admin auth and security baseline [COMPLETED]
### Scope & Deliverables
- Password hashing with argon2-cffi (`app/auth.py`).
- Session management using Starlette SessionMiddleware with signed cookies (HttpOnly, SameSite=Lax, Secure in production).
- CSRF protection (`app/security.py`) for state-changing POST/PUT/DELETE requests via forms and HTMX headers.
- DB-backed rate limiting (`app/rate_limit.py`) blocking on 6th failed attempt within 15 minutes per IP+email, returning HTTP 429.
- Admin CLI command (`python -m app.cli create-admin`).
- Initial admin seeding on first start if `ADMIN_EMAIL` and `ADMIN_PASSWORD` are configured and no admin exists.
- `require_admin` dependency protecting admin routes.
- Startup check refusing to start in production if `SECRET_KEY` equals default.
### Files Created
- `app/auth.py`
- `app/security.py`
- `app/rate_limit.py`
- `app/cli.py`
- `app/routes/__init__.py`
- `app/routes/auth.py`
- `app/templates/login.html`
### Tests Needed
- `tests/test_auth.py`: Login success, identical generic error for invalid password or nonexistent email, rate limiting triggering on 6th failure, cookie security flags.
- `tests/test_csrf.py`: Parametrized test discovering all state-changing endpoints dynamically and ensuring rejection without valid CSRF or valid session.
- `tests/test_security_startup.py`: Assert startup rejection when `ENV=production` and default `SECRET_KEY`.

---

## M3: Notices [COMPLETED]
### Scope & Deliverables
- Admin CRUD for Notices: title (max 150), plain-text body (line breaks preserved), category (General, Academic, Exam, Event, Scholarship, Job), pinned, optional external link (http/https only), optional batch, draft/published, published_at.
- Public notice board at `/`: pinned notices first, then newest published_at; search (title + body); category and batch filters; 10 items per pagination page; works without JS, enhanced with HTMX.
- Notice detail page (`/notices/{id}`).
- Custom 404 page for missing notice.
- Strict XSS protection (plain text escaped) and link scheme allowlist.
### Files Created
- `app/routes/notices.py`
- `app/templates/notices/index.html`
- `app/templates/notices/detail.html`
- `app/templates/notices/form.html`
- `app/templates/notices/_list_partial.html`
- `app/templates/errors/404.html`
### Tests Needed
- `tests/test_notices.py`: Ordering (pinned first, then newest), drafts excluded from public views, pagination out-of-range behavior (redirect to last page), search query filtering, XSS escaping, safe external link validation.

---

## M4: Batches, routine, exams [COMPLETED]
### Scope & Deliverables
- Admin CRUD for Batches and Sections (`/admin/batches`).
- Admin CRUD for Routine Slots (`/admin/routine`) with conflict validations:
  - End time > start time.
  - No overlap for same batch + section.
  - No room double-booking.
  - No teacher double-booking (trimmed, case-insensitive).
  - Clear error message naming the conflicting slot.
  - Touching intervals (e.g. 10:00-11:00 and 11:00-12:00) permitted.
- Public weekly routine grid per batch and section (`/routine`).
- Public "Today" routine page (`/today`) evaluated in `TIMEZONE` (default Asia/Dhaka).
- Admin CRUD for Exams (`/admin/exams`): batch, course, type (Class Test/Midterm/Final/Lab), date, start time, room, note.
- Public "Upcoming exams" page (`/exams`): sorted by date, past exams hidden with toggle to show.
### Files Created
- `app/routes/batches.py`
- `app/routes/routine.py`
- `app/routes/exams.py`
- `app/templates/batches/index.html`
- `app/templates/batches/form.html`
- `app/templates/routine/grid.html`
- `app/templates/routine/today.html`
- `app/templates/routine/form.html`
- `app/templates/exams/index.html`
- `app/templates/exams/form.html`
### Tests Needed
- `tests/test_batches.py`: Batch & section CRUD, deletion cascade/block rules.
- `tests/test_routine.py`: Overlap boundary conditions, room/teacher conflicts, Today page timezone boundary behavior across midnight.
- `tests/test_exams.py`: Exam CRUD, sorting by date, past exam filtering and toggle.

---

## M5: Feeds
### Scope & Deliverables
- `/feeds/notices.atom`: Up to 30 latest published notices, absolute URLs with `PUBLIC_BASE_URL`, draft exclusion.
- `/feeds/batch/{id}.ics`: iCalendar format with TZID, recurring weekly routine slots formatted with RRULE between `TERM_START` and `TERM_END`, one-off exam events, stable UIDs.
- Feed subscription instructions and UI links.
### Files Created
- `app/routes/feeds.py`
- `app/feeds.py`
### Tests Needed
- `tests/test_feeds.py`: Atom feed schema validity, exclusion of drafts, ICS validity with `icalendar` parser, RRULE and TZID presence, UID stability, 404 on missing batch.

---

## M6: Audit log, hardening, seed, mobile UI, end-to-end tests
### Scope & Deliverables
- Audit log recording on all admin mutations (actor, action, entity, id, time, summary).
- Admin paginated audit log viewer (`/admin/audit`).
- Security headers middleware (strict CSP without inline scripts, X-Content-Type-Options, Referrer-Policy, frame-ancestors none).
- Vendored HTMX (eval disabled, no `hx-on`).
- Custom 500 error page.
- Idempotent seed script (`python -m app.seed`).
- Mobile UI styling (no horizontal scroll at 375px width).
- Playwright E2E tests covering complete flows and JS-disabled functionality.
### Files Created
- `app/audit.py`
- `app/routes/audit.py`
- `app/seed.py`
- `app/static/js/htmx.min.js`
- `app/static/js/htmx.LICENSE.md`
- `app/static/css/app.css`
- `app/templates/audit/index.html`
- `app/templates/errors/500.html`
### Tests Needed
- `tests/test_audit.py`: Mutation audit trail completeness.
- `tests/test_seed.py`: Seed idempotence on repeated execution.
- `tests/test_security_headers.py`: CSP and security headers presence.
- `tests/test_e2e.py`: Playwright end-to-end tests (G6, G4, G5).
