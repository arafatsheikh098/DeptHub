PROJECT: DeptHub
PURPOSE: A public website where students of one university department see notices, their class routine and upcoming exams, and where department staff (admins) manage that content. Works well on phones.

IN SCOPE
F1 Admin auth: login/logout; argon2 password hashing (argon2-cffi); signed session cookie (HttpOnly, SameSite=Lax, Secure in production); CSRF protection on every state-changing request; login rate limit (5 failures per 15 minutes per IP+email, stored in the database); admin created by CLI (python -m app.cli create-admin) or seeded from ADMIN_EMAIL/ADMIN_PASSWORD on first start only if no admin exists; app refuses to start in production with the default SECRET_KEY.
F2 Notices: admin CRUD. Fields: title (max 150), plain-text body (line breaks preserved), category (General, Academic, Exam, Event, Scholarship, Job), pinned flag, optional external link (http/https only), optional batch (empty = all batches), draft/published, published_at. Public home page: pinned first, then newest; search (title + body, case-insensitive); category filter; batch filter; 10 per page; works without JavaScript (HTMX only enhances).
F3 Batches and sections: admin CRUD (example batch name: "22-23 Session"; sections optional, e.g. A, B).
F4 Routine: admin CRUD for weekly slots: batch, optional section, weekday, start time, end time, course code, course title, teacher, room. Validation: end after start; no overlap for the same batch+section; no room double-booking; no teacher double-booking (trimmed, case-insensitive); clear error messages naming the conflicting slot. Public weekly grid per batch/section and a "Today" page computed in TIMEZONE.
F5 Exams: admin CRUD (batch, course, type: Class Test/Midterm/Final/Lab, date, start time, room, note). Public "Upcoming exams" sorted by date; past exams hidden with a "show past" toggle.
F6 Feeds: /feeds/notices.atom (latest 30 published notices, absolute URLs from PUBLIC_BASE_URL) and /feeds/batch/{id}.ics (weekly recurring routine events with TZID and RRULE for the term window TERM_START..TERM_END, plus one-off exam events; stable UIDs).
F7 Audit log: every admin create/update/delete is recorded (actor, action, entity, id, time, short summary); admin-only paginated page.
F8 Operations: GET /health (checks the database); structured logs; security headers (CSP without inline scripts, X-Content-Type-Options, Referrer-Policy, frame-ancestors none); custom 404/500 pages; idempotent demo seed (python -m app.seed); all timestamps stored in UTC and shown in TIMEZONE (default Asia/Dhaka).

OUT OF SCOPE
Student accounts or signup, email/SMS/Telegram notifications, file uploads, comments, multi-department tenancy, admin-user management UI, translations, JSON REST API, analytics, dark mode, markdown rendering, anything not listed above.

ALLOWED STACK
Python 3.12; FastAPI; uvicorn; SQLModel; Alembic; psycopg[binary]; pydantic-settings; Jinja2; python-multipart; argon2-cffi; icalendar; Starlette SessionMiddleware; vendored HTMX (eval disabled) and vendored Pico.css (license files kept); pytest, pytest-playwright, httpx, freezegun; ruff; Docker, docker compose; GitHub Actions. Nothing else without a BACKLOG entry.

GLOBAL ACCEPTANCE CRITERIA
G1 docker compose up --build on a fresh clone serves the site at http://localhost:8000; demo data loads with the documented seed command.
G2 Every feature F1-F8 is covered by named tests; CI (with a Postgres service) is green.
G3 A parametrized test discovers all state-changing routes from the app and proves each rejects (a) no session and (b) missing/invalid CSRF token.
G4 Public pages (home, notice detail, routine, today, exams) work with JavaScript disabled.
G5 No horizontal scroll at 375px width on any public page (Playwright check).
G6 End-to-end: admin posts a pinned notice, visitor sees it first; admin adds a Monday class, Today page shows it when the clock is frozen to that Monday in TIMEZONE.

MILESTONES
M1 Foundation; M2 Admin auth and security baseline; M3 Notices; M4 Batches, routine, exams; M5 Feeds; M6 Audit log, hardening, seed, mobile UI, end-to-end tests.
