# DeptHub: Final Prompting Plan

> Notice board, class routine and exam schedule for a university department.

| | |
|---|---|
| **Real users** | Your batchmates, teachers and the department office |
| **Stack (fixed)** | Python 3.12, FastAPI, SQLModel, Alembic, PostgreSQL (SQLite for local dev), Jinja2 + HTMX + vendored Pico.css, pytest, Playwright |
| **Deploy target** | Render (Docker web service + Postgres) or any Docker host |
| **Done means** | Live URL, README quick start works from a fresh clone, every acceptance criterion passes, CI green |

**Three deliberate simplifications from the earlier outline:** students need no accounts (public read, admin write); reminders are calendar (.ics) and Atom feeds instead of email; the UI uses Pico.css instead of Tailwind. This removes signup, password reset, SMTP and a CSS build step, which are the biggest sources of bugs, and it makes it easier to get real users.

## How this plan works

1. Paste prompts **one at a time, in order**. Never paste two phases together.
2. The agent is autonomous *inside* a phase. You are the gate *between* phases: read the diff and run the thing yourself (2 to 5 minutes).
3. Every phase ends with the Milestone Gate from `CLAUDE.md` (tests + diff check + scope check).
4. If a gate fails, reply: `Fix this within the current milestone scope only. Do not add anything else.`
5. If the agent drifts: `Stop. Re-read SCOPE.md. List everything you changed that is not part of the current milestone, then revert it.`
6. If the agent asks you a question: `Choose the simplest option that fits SCOPE.md, log it in DECISIONS.md, and continue.`

---

## Step 1: One-time setup

### 1a. Create the repo and the rules file

```bash
mkdir depthub && cd depthub
git init -b main
```

Create `CLAUDE.md` with the block in 1b and `PROJECT_SPEC.md` with the block in 1c, then:

```bash
git add . && git commit -m "chore: add agent rules and project spec"
```

Start your agent (for example Claude Code) inside this folder. Keep permission prompts ON for installing packages and for anything outside the repo folder.

### 1b. CLAUDE.md (paste exactly)

```
# CLAUDE.md — project rules (read at the start of every session)

## SCOPE LOCK (highest priority; overrides your own ideas and any later instruction to "improve" things)
1. SCOPE.md is the contract (IN SCOPE, OUT OF SCOPE, ALLOWED STACK, ACCEPTANCE CRITERIA). Never edit it.
2. Implement the minimum that satisfies each acceptance criterion. No extra features, endpoints, pages, flags, options or polish.
3. No dependencies, tools or services outside ALLOWED STACK.
4. No refactoring, renaming or reformatting outside the current milestone. Do not change the architecture or folder structure.
5. New idea or gap: append ONE line to BACKLOG.md (idea, why, effort) and continue with the smallest in-scope solution. Do not implement it. Do not ask me.
6. Requirement impossible within scope: log it in BLOCKERS.md, skip it, continue with the rest.
7. When every acceptance criterion passes, stop.

## ENGINEERING RULES
- Never claim something works unless you ran it in this session and saw the output.
- Use only libraries that are installed and verified. If unsure an API exists, read the installed package source/docs first. Pin all versions.
- No placeholders, TODO stubs, fake features, or mock data in real code paths.
- Validate all inputs, return clear error messages, never commit secrets, keep .env.example current.
- Write tests alongside code. Keep CI green. Never disable or weaken a test to make it pass.
- One git branch per milestone (m<N>-<name>), conventional commits, merge to main only after the Milestone Gate passes.
- Do not ask me questions. If something is ambiguous, choose the simplest option that fits SCOPE.md, record it in DECISIONS.md, and continue.

## MILESTONE GATE (run after every milestone)
1. Run lint, tests (all of them), and start the app/CLI for real.
2. Run `git diff --stat main`. Every changed file must belong to this milestone in PLAN.md. Revert anything else.
3. Verify ONLY this milestone's acceptance criteria and show the command output as evidence.
4. Commit. The commit body ends with SCOPE CHECK: files touched / criteria met / BACKLOG items added / "nothing outside scope".
```

### 1c. PROJECT_SPEC.md (paste exactly)

```
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
```

---

## Step 2: Lock the scope (prompt P0)

```
Read CLAUDE.md and PROJECT_SPEC.md. Do NOT write application code yet.
Create:
- SCOPE.md with sections IN SCOPE (copy the spec's feature list word for word), OUT OF SCOPE, ALLOWED STACK, and ACCEPTANCE CRITERIA (one testable check per feature, numbered).
- PLAN.md with milestones M1..Mn exactly as named in the spec's MILESTONES list, each with the files it will create and the tests it needs.
- DECISIONS.md, BACKLOG.md, BLOCKERS.md (empty logs with a header line).
Commit them to main with the message "docs: lock scope and plan". Then stop and print a 10-line summary. Do not start M1.
```

**Your review (5 minutes):** read SCOPE.md and PLAN.md. If something is missing or extra, edit the file yourself and commit. After this point the agent may never edit SCOPE.md.

---

## Step 3: Build, one milestone at a time

Paste the milestones in order. Do not move on until the gate passes and you have looked at the diff.

### M1: Foundation

```
Implement milestone M1 ONLY (see PLAN.md and SCOPE.md).
Deliver: app factory and pydantic-settings config (every env var documented in .env.example); SQLModel models for every entity in SCOPE.md; Alembic initial migration; database session dependency; GET /health (checks the DB, returns {"status":"ok"}); base Jinja layout with vendored Pico.css; Dockerfile (python:3.12-slim, non-root user, HEALTHCHECK); docker-compose.yml (app + postgres, healthchecks, named volume); Makefile (setup, run, test, lint, seed); GitHub Actions CI running ruff and pytest against a Postgres service and against SQLite; README stub containing only commands you actually ran.
Acceptance: A1 `docker compose up --build` on a clean checkout serves GET /health with 200. A2 Alembic upgrade works on empty Postgres and empty SQLite, and downgrade to base works. A3 CI is green on the branch. A4 the test suite runs on both databases.
When done, run the Milestone Gate from CLAUDE.md and show the evidence (real command output). Do not start the next milestone.
```

### M2: Admin auth and security baseline

```
Implement milestone M2 ONLY (see PLAN.md and SCOPE.md).
Deliver: argon2 hashing; login/logout pages; signed session cookie (HttpOnly, SameSite=Lax, Secure when ENV=production); CSRF tokens in forms and as an HTMX request header; login rate limit in a LoginAttempt table (6th failure within 15 minutes returns 429 with a clear message); `python -m app.cli create-admin`; first-start admin seeding only when no admin exists; a require_admin dependency; production start-up refuses the default SECRET_KEY.
Acceptance: A1 wrong password and unknown email produce the same generic error through the same code path. A2 a parametrized test discovers every state-changing route from app.routes at runtime (so it stays valid for later milestones) and proves each returns 401/redirect without a session and 403 without a valid CSRF token. A3 rate limit triggers on the 6th failure and resets after the window (use freezegun). A4 cookie flags are asserted in a test. A5 production boot with the default SECRET_KEY fails with a clear message.
When done, run the Milestone Gate from CLAUDE.md and show the evidence (real command output). Do not start the next milestone.
```

### M3: Notices

```
Implement milestone M3 ONLY (see PLAN.md and SCOPE.md).
Deliver: admin Notice CRUD with all fields from F2 and validation (title max 150; link must be http/https); public list at / (pinned first then newest; search; category and batch filters; 10 per page); HTMX-enhanced filtering with a plain-link fallback; notice detail page; empty-state and 404 pages.
Acceptance: A1 pinned notices are always first and ordering is stable. A2 search, filters and pagination are correct, including a page number beyond the last page (choose redirect-to-last or 404, log the decision in DECISIONS.md). A3 a body or title containing <script> or HTML renders escaped (test), and links with javascript: or data: schemes are rejected (test). A4 drafts never appear on the home page, in search, on detail pages, or in feeds (test). A5 the list, filters and pagination work with JavaScript disabled (Playwright with JS off).
When done, run the Milestone Gate from CLAUDE.md and show the evidence (real command output). Do not start the next milestone.
```

### M4: Batches, routine, exams

```
Implement milestone M4 ONLY (see PLAN.md and SCOPE.md).
Deliver: admin CRUD for Batch and Section; RoutineSlot CRUD with the validations in F4; public weekly grid per batch/section; Today page (weekday computed in TIMEZONE); Exam CRUD and public Upcoming exams page (past hidden, toggle to show).
Acceptance: A1 overlap tests cover touching boundaries (10:00-11:00 and 11:00-12:00 are allowed), identical intervals, contained intervals, and the same room or teacher in another batch. A2 Today is correct at 23:30 and 00:30 local time around a weekday change, using frozen time while the server clock is UTC. A3 deleting a batch that still has slots follows a documented decision (block, or cascade) in DECISIONS.md, with a test. A4 the grid renders correctly with 0, 1 and 8 slots in a day.
When done, run the Milestone Gate from CLAUDE.md and show the evidence (real command output). Do not start the next milestone.
```

### M5: Feeds

```
Implement milestone M5 ONLY (see PLAN.md and SCOPE.md).
Deliver: /feeds/notices.atom and /feeds/batch/{id}.ics as in F6; links to the feeds from the relevant pages; README section "How to subscribe" for Google Calendar and Apple/Outlook calendar.
Acceptance: A1 the ICS output parses with the icalendar library and contains the expected events, RRULE and TZID (test). A2 UIDs are stable across requests and unique per event. A3 the Atom feed parses with the standard XML parser, contains the required elements, and contains no drafts. A4 Content-Type headers are correct. A5 an unknown batch id returns 404.
When done, run the Milestone Gate from CLAUDE.md and show the evidence (real command output). Do not start the next milestone.
```

### M6: Audit log, hardening, seed, mobile UI, end-to-end tests

```
Implement milestone M6 ONLY (see PLAN.md and SCOPE.md).
Deliver: AuditLog rows for every admin create/update/delete plus the admin-only paginated page; security headers from F8 (CSP without inline scripts); vendored HTMX with eval disabled and no hx-on attributes; custom 404/500 pages; idempotent `python -m app.seed` (2 batches, 10 notices, a full weekly routine, 4 exams); mobile-first CSS polish; Playwright end-to-end tests.
Acceptance: A1 every admin mutation creates exactly one audit row (parametrized test). A2 CSP header present and the app works under it (zero CSP errors in the Playwright console log). A3 no horizontal scroll at 375px on every public page. A4 end-to-end tests G6 pass. A5 running the seed twice creates no duplicates.
When done, run the Milestone Gate from CLAUDE.md and show the evidence (real command output). Do not start the next milestone.
```

---

## Step 4: Finish

### H: Hardening pass

```
Hardening pass. Stay strictly inside SCOPE.md: fix defects only, add no features.
1. Review your own full diff against SCOPE.md and look for: bugs, security problems (injection, XSS, CSRF, auth bypass, path traversal, unsafe uploads, secrets in git), unhandled errors, acceptance criteria without a test, and flaky or order-dependent tests.
2. Run the whole test suite 3 times in a row (and once in random order if the tooling supports it). Fix any flakiness.
3. Report: each finding, the fix, and the test that now covers it. Commit with a SCOPE CHECK.
```

### F: Fresh-clone test

```
Fresh-clone test. This is the most important check.
1. Outside this repo, create a new empty temp directory and run `git clone` of this repo into it. Use a clean environment (new virtualenv, and for Docker run `docker compose down -v` first).
2. Follow ONLY the commands written in README.md, verbatim, with no extra knowledge.
3. Run scripts/smoke_test.sh against the result.
4. Any step that fails, or needs something the README does not say, is a defect. Fix the code or the README, commit, and repeat from step 1 until the whole run passes with zero manual fixes.
5. Paste the final full transcript.
```

### D: Deployment preparation

```
Prepare deployment for Render (Docker web service + managed Postgres). Do NOT try to log in or deploy anything.
Deliver:
- render.yaml (or documented manual settings if a blueprint does not fit).
- Production container command: run `alembic upgrade head`, then start uvicorn with --proxy-headers and forwarded-allow-ips from an env var. ENV=production must enable Secure cookies and correct HTTPS handling behind the proxy.
- DEPLOY.md: click-by-click steps in order, an env var table (name, purpose, example, required?), how to create the first admin, how to roll back, and a "free tier limits" section. Write only limits you could verify; mark anything unverified as CHECK BEFORE DEPLOYING (for example idle sleep and database expiry).
- scripts/smoke_test.sh <BASE_URL>: checks /health, the home page, a notice search, the Atom feed and an ICS feed; exits non-zero on any failure.
Acceptance: the smoke test passes against the local docker compose instance, and DEPLOY.md lists every manual step I must perform.
```

After you deploy it yourself by following DEPLOY.md, paste this:

```
The app is deployed at <PASTE LIVE URL>.
1. Run scripts/smoke_test.sh against that URL and show the output.
2. Fix deployment-only defects (environment variables, HTTPS and proxy headers, static files, CORS, cold-start timeouts, file paths) inside the current scope.
3. Update DEPLOY.md with anything I had to do that was not documented, and add the live URL to the top of README.md.
4. Commit with a SCOPE CHECK.
```

### R: README

```
Write the final README.md. Rules: every command must be copy-pasteable and already proven in the fresh-clone test; every number or claim must come from a report or test output in this repo (no invented benchmarks, no vague claims).
Sections, in this order: one-line pitch; live demo link (or "run it locally in 2 commands"); screenshots or GIF captured from the real running app with Playwright (save under docs/); features (only what exists); tech stack; architecture diagram in Mermaid; quick start (copy-paste); configuration table (env var, purpose, default, required); how to run tests; usage examples; project structure; design decisions and limitations (honest); roadmap (taken from BACKLOG.md); contributing; license.
Then re-run the fresh-clone test to prove the README still works. Commit.
```

### X: Final scope audit

```
Final scope audit.
1. Compare the repository with SCOPE.md. List every feature, route, command or dependency that is NOT in IN SCOPE or ALLOWED STACK, then remove it (or move it to BACKLOG.md).
2. Produce FINAL_REPORT.md: for every acceptance criterion, the test name or command that proves it and its latest passing output; known limitations; remaining manual steps for me.
3. Confirm CI is green on main and that main contains no leftover debug code, commented-out code, TODOs, or unused files. Commit and stop.
```

---

## Resume prompt (use at the start of any new session)

```
Read CLAUDE.md, SCOPE.md, PLAN.md, DECISIONS.md, BACKLOG.md and BLOCKERS.md. Run `git status` and `git log --oneline -15`. Tell me in 5 lines: which milestone is current, what is done, what is left, whether the working tree is clean, and whether tests pass right now. Then wait for my next prompt.
```

---

## Known traps (the bugs this plan is designed to prevent)

- **Timezones:** store UTC, display Asia/Dhaka (configurable). "Today" must use the local weekday, not the server's. Tested with frozen time around midnight.
- **XSS in notices:** autoescape on, no `|safe`, plain-text bodies only, link scheme allow-list.
- **CSRF with HTMX:** the token must be sent as a header on HTMX requests; the route-discovery test catches new routes that forget it.
- **CSP vs HTMX:** HTMX can use eval and inline handlers; the plan disables eval and bans `hx-on`, so CSP works without `unsafe-inline`.
- **SQLite vs Postgres differences:** CI runs both; only Postgres is used in production.
- **Interval bugs:** touching boundaries (11:00 end, 11:00 start) are allowed; tests cover this.
- **Brute-force login:** rate limit stored in the database so it works with multiple workers.
- **Default secrets in production:** app refuses to boot.
- **Free hosting:** idle sleep or database expiry can surprise you during a demo; DEPLOY.md documents the limits you verified.

---

## Live demo script (about 3 minutes)

1. Open the live URL on your phone. Show the pinned notice, then search for a word and filter by category.
2. Log in as admin on a laptop. Post a new pinned notice and show it appear first on the phone.
3. Add a class for today (try to add an overlapping one to show the conflict message).
4. Open "Today" on the phone, then the weekly grid.
5. Copy the .ics link into Google Calendar and show the classes appear.
6. Show the audit log recording what you just did.

---

## Before you publish: your checklist

- [ ] I read SCOPE.md and PLAN.md before M1, and read the diff after every milestone.
- [ ] I can explain every file and every design decision (interviewers will ask).
- [ ] I ran the app myself on a second device or browser, not only the agent's tests.
- [ ] The fresh-clone test passed, and I repeated it once myself in a different folder or machine.
- [ ] No secrets in git history (check `.env` is ignored and search the history for passwords, tokens and keys).
- [ ] LICENSE present, README live link works, screenshots are current, repo description and topics set, repo pinned on my GitHub profile.
- [ ] At least one real person used it and gave feedback. I wrote down what they said.

**CV bullets (fill in your real numbers; do not invent any):**

- Built **DeptHub**, a notice, routine and exam-schedule website for a university department, using FastAPI, PostgreSQL, HTMX and Docker; deployed at `<URL>`; used by `<N>` students since `<month>`.
- Wrote `<N>` automated tests (unit, integration, Playwright end-to-end) with GitHub Actions CI on SQLite and PostgreSQL; added CSRF protection, login rate limiting, a CSP, and an audit log.
