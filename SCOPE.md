# SCOPE

## IN SCOPE
F1 Admin auth: login/logout; argon2 password hashing (argon2-cffi); signed session cookie (HttpOnly, SameSite=Lax, Secure in production); CSRF protection on every state-changing request; login rate limit (5 failures per 15 minutes per IP+email, stored in the database); admin created by CLI (python -m app.cli create-admin) or seeded from ADMIN_EMAIL/ADMIN_PASSWORD on first start only if no admin exists; app refuses to start in production with the default SECRET_KEY.
F2 Notices: admin CRUD. Fields: title (max 150), plain-text body (line breaks preserved), category (General, Academic, Exam, Event, Scholarship, Job), pinned flag, optional external link (http/https only), optional batch (empty = all batches), draft/published, published_at. Public home page: pinned first, then newest; search (title + body, case-insensitive); category filter; batch filter; 10 per page; works without JavaScript (HTMX only enhances).
F3 Batches and sections: admin CRUD (example batch name: "22-23 Session"; sections optional, e.g. A, B).
F4 Routine: admin CRUD for weekly slots: batch, optional section, weekday, start time, end time, course code, course title, teacher, room. Validation: end after start; no overlap for the same batch+section; no room double-booking; no teacher double-booking (trimmed, case-insensitive); clear error messages naming the conflicting slot. Public weekly grid per batch/section and a "Today" page computed in TIMEZONE.
F5 Exams: admin CRUD (batch, course, type: Class Test/Midterm/Final/Lab, date, start time, room, note). Public "Upcoming exams" sorted by date; past exams hidden with a "show past" toggle.
F6 Feeds: /feeds/notices.atom (latest 30 published notices, absolute URLs from PUBLIC_BASE_URL) and /feeds/batch/{id}.ics (weekly recurring routine events with TZID and RRULE for the term window TERM_START..TERM_END, plus one-off exam events; stable UIDs).
F7 Audit log: every admin create/update/delete is recorded (actor, action, entity, id, time, short summary); admin-only paginated page.
F8 Operations: GET /health (checks the database); structured logs; security headers (CSP without inline scripts, X-Content-Type-Options, Referrer-Policy, frame-ancestors none); custom 404/500 pages; idempotent demo seed (python -m app.seed); all timestamps stored in UTC and shown in TIMEZONE (default Asia/Dhaka).

## OUT OF SCOPE
Student accounts or signup, email/SMS/Telegram notifications, file uploads, comments, multi-department tenancy, admin-user management UI, translations, JSON REST API, analytics, dark mode, markdown rendering, anything not listed above.

## ALLOWED STACK
Python 3.12; FastAPI; uvicorn; SQLModel; Alembic; psycopg[binary]; pydantic-settings; Jinja2; python-multipart; argon2-cffi; icalendar; Starlette SessionMiddleware; vendored HTMX (eval disabled) and vendored Pico.css (license files kept); pytest, pytest-playwright, httpx, freezegun; ruff; Docker, docker compose; GitHub Actions. Nothing else without a BACKLOG entry.

## ACCEPTANCE CRITERIA
1. AC-F1.1: Admin can log in with valid credentials and receive a signed session cookie (HttpOnly, SameSite=Lax, Secure when ENV=production).
2. AC-F1.2: Incorrect password or non-existent email return the exact same generic error through the same code path.
3. AC-F1.3: All state-changing endpoints reject requests lacking a valid session (401/redirect) or lacking a valid CSRF token (403).
4. AC-F1.4: 6th consecutive failed login for an IP+email within 15 minutes returns 429 with a clear rate-limit message; attempts reset after 15 minutes.
5. AC-F1.5: Admin user can be created via CLI (`python -m app.cli create-admin`) and is seeded on initial start if ADMIN_EMAIL/ADMIN_PASSWORD are set and no admin exists.
6. AC-F1.6: Application refuses to start in production if SECRET_KEY is set to the default value.
7. AC-F2.1: Admin can create, read, update, and delete notices with all fields (title max 150, plain-text body with preserved newlines, category, pinned, external http/https link, optional batch, draft/published, published_at).
8. AC-F2.2: Public home page lists published notices (10 per page) with pinned notices first, followed by newest `published_at`; drafts are never shown publicly.
9. AC-F2.3: Case-insensitive search on title/body and category/batch filtering work with and without JavaScript enabled.
10. AC-F2.4: Notice bodies render text escaped against XSS; non-http/https external links are rejected.
11. AC-F3.1: Admin can create, read, update, and delete batches and sections.
12. AC-F4.1: Admin can create, read, update, and delete routine slots with validation (end time > start time).
13. AC-F4.2: Conflict validation prevents overlapping slots for the same batch/section, room double-booking, and teacher double-booking (case-insensitive/trimmed), returning a descriptive error naming the conflicting slot.
14. AC-F4.3: Public weekly routine grid displays per batch/section; "Today" routine accurately computes the current weekday in configured TIMEZONE (including across midnight transitions).
15. AC-F5.1: Admin can create, read, update, and delete exams (batch, course, type, date, start time, room, note).
16. AC-F5.2: Public upcoming exams page lists future exams sorted by date; past exams are hidden by default with a working "show past" toggle.
17. AC-F6.1: `/feeds/notices.atom` serves valid Atom XML with up to 30 latest published notices using absolute URLs from `PUBLIC_BASE_URL`.
18. AC-F6.2: `/feeds/batch/{id}.ics` serves valid iCalendar data with stable UIDs, TZID, recurring RRULE slots within `TERM_START`..`TERM_END`, and one-off exam events; 404 for nonexistent batch.
19. AC-F7.1: Every admin create, update, and delete operation writes an AuditLog record (actor, action, entity, id, time, summary).
20. AC-F7.2: Admin can view a paginated list of audit logs.
21. AC-F8.1: `GET /health` checks database connectivity and returns `{"status": "ok"}`.
22. AC-F8.2: Security headers (strict CSP without unsafe-inline scripts, X-Content-Type-Options, Referrer-Policy, X-Frame-Options / frame-ancestors none) are present on responses.
23. AC-F8.3: Custom 404 and 500 error pages are served.
24. AC-F8.4: `python -m app.seed` is idempotent and populates demo data without duplicating records.
25. AC-F8.5: All timestamps are stored in UTC and rendered in TIMEZONE (default Asia/Dhaka).
26. AC-G1: `docker compose up --build` on a fresh checkout serves the application at http://localhost:8000 with seed data.
27. AC-G2: All public pages have no horizontal scroll at 375px viewport width and work with JavaScript disabled.
