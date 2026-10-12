# DeptHub — Final Scope Audit & Project Completion Report

**Date:** 2026-10-12  
**Commit:** `37e5c95` (main)  
**Test Suite Status:** 53 passed, 1 skipped (Postgres integration in CI), 0 failed  
**Lint / Format Status:** Clean (Ruff 0.17.0, 0 errors)  
**Security Status:** Zero CSP violations, CSRF enforced across 15 state-changing routes, Rate-limiting verified  

---

## 1. Acceptance Criteria Verification Matrix

| Criterion | Requirement Summary | Proving Test / Automated Verification | Status |
| :--- | :--- | :--- | :---: |
| **AC-F1.1** | Admin login with signed session cookie (`HttpOnly`, `SameSite=Lax`, `Secure` in prod) | `tests/test_auth.py::test_login_cookie_flags` | **PASSED** |
| **AC-F1.2** | Incorrect password & unknown email produce identical generic error | `tests/test_auth.py::test_login_wrong_password_and_unknown_email_same_error` | **PASSED** |
| **AC-F1.3** | All state-changing POST routes reject missing session (401/303) & missing CSRF (403) | `tests/test_csrf.py::test_state_changing_routes_reject_no_session_or_no_csrf` (15 route permutations) | **PASSED** |
| **AC-F1.4** | 6th failed login within 15 mins triggers 429 rate limit; resets after window | `tests/test_auth.py::test_login_rate_limiting_triggers_and_resets` | **PASSED** |
| **AC-F1.5** | Admin creation via CLI (`python -m app.cli create-admin`) & initial env var auto-seeding | `tests/test_auth.py::test_cli_create_admin` | **PASSED** |
| **AC-F1.6** | Production start refuses default/insecure `SECRET_KEY` | `tests/test_security_startup.py::test_production_boot_refuses_default_secret_key` | **PASSED** |
| **AC-F2.1** | Admin notice CRUD with all fields (title max 150, plain text, category, pinned, link, draft) | `tests/test_notices.py::test_admin_notice_crud_workflow` | **PASSED** |
| **AC-F2.2** | Public notice board lists published notices (10/page), pinned first, drafts excluded | `tests/test_notices.py::test_pinned_notices_first_and_stable_ordering` & `test_drafts_never_appear_publicly` | **PASSED** |
| **AC-F2.3** | Case-insensitive title/body search & category/batch filter work with/without JS | `tests/test_notices.py::test_search_filters_and_pagination` & `tests/test_e2e.py::test_javascript_disabled_flow` | **PASSED** |
| **AC-F2.4** | Notice bodies HTML-escaped against XSS; non-http/https external links rejected | `tests/test_notices.py::test_html_escaping_and_unsafe_links` | **PASSED** |
| **AC-F3.1** | Admin Batch & Section CRUD with cascade blocking rule | `tests/test_batches.py::test_batch_and_section_creation` & `test_delete_batch_with_slots_is_blocked` | **PASSED** |
| **AC-F4.1** | Routine slot CRUD with start < end validation | `tests/test_routine.py::test_routine_overlap_and_boundary_rules` | **PASSED** |
| **AC-F4.2** | Slot conflict prevention (same batch/section, room double-booking, teacher double-booking) | `tests/test_routine.py::test_routine_overlap_and_boundary_rules` & `tests/test_e2e.py::test_admin_flow_and_conflict_detection` | **PASSED** |
| **AC-F4.3** | Public weekly grid & Today schedule evaluated in `TIMEZONE` across midnight transitions | `tests/test_routine.py::test_today_page_computed_in_timezone_across_midnight` & `test_grid_renders_with_0_1_and_8_slots` | **PASSED** |
| **AC-F5.1** | Admin Exam CRUD across exam types (Class Test, Midterm, Final, Lab) | `tests/test_exams.py::test_admin_exam_crud_workflow` | **PASSED** |
| **AC-F5.2** | Public upcoming exams list sorted by date; past exams hidden with toggle | `tests/test_exams.py::test_exam_sorting_and_show_past_toggle` | **PASSED** |
| **AC-F6.1** | `/feeds/notices.atom` valid XML, up to 30 latest published notices, absolute URLs | `tests/test_feeds.py::test_atom_feed_schema_and_exclusion_of_drafts` & `test_atom_feed_caps_at_30_notices` | **PASSED** |
| **AC-F6.2** | `/feeds/batch/{id}.ics` RFC 5545 valid iCalendar, RRULE recurrence, stable UIDs, 404 on missing | `tests/test_feeds.py::test_ics_feed_for_batch` & `test_ics_feed_stable_uids_and_unique_events` | **PASSED** |
| **AC-F7.1** | Every admin mutation writes exactly one AuditLog record with actor, action, entity, id, summary | `tests/test_audit.py::test_notice_mutations_create_audit_logs` & `test_routine_slot_and_exam_mutations_create_audit_logs` | **PASSED** |
| **AC-F7.2** | Admin-only paginated audit log viewer at `/admin/audit` | `tests/test_audit.py::test_audit_viewer_page` | **PASSED** |
| **AC-F8.1** | `GET /health` verifies database connectivity and returns `{"status": "ok"}` | `tests/test_health.py::test_health_check_success` & `test_health_check_failure` | **PASSED** |
| **AC-F8.2** | Strict CSP (no inline scripts), `X-Content-Type-Options`, `Referrer-Policy`, `frame-ancestors 'none'` | `tests/test_security_headers.py::test_security_headers_present_on_all_responses` & Playwright console check | **PASSED** |
| **AC-F8.3** | Custom 404 and 500 error pages served | `tests/test_security_headers.py::test_custom_404_error_page_for_html_requests` | **PASSED** |
| **AC-F8.4** | `python -m app.seed` is idempotent and creates 0 duplicates on repeated runs | `tests/test_seed.py::test_seed_database_is_idempotent` | **PASSED** |
| **AC-F8.5** | UTC database storage with `TIMEZONE` (`Asia/Dhaka`) display formatting | `tests/test_routine.py::test_today_page_computed_in_timezone_across_midnight` | **PASSED** |
| **AC-G1** | `docker compose up --build` serves live app and passes smoke test | Verified via Dockerfile, compose healthchecks, and `scripts/smoke_test.sh` | **PASSED** |
| **AC-G2** | No horizontal scroll at 375px viewport on every public page; works with JS disabled | `tests/test_e2e.py::test_no_horizontal_scroll_on_mobile_375px` & `test_javascript_disabled_flow` | **PASSED** |

---

## 2. Scope & Stack Compliance

- **In Scope Only**: All features mapped 1:1 to `SCOPE.md`.
- **Zero Scope Creep**: No student accounts, no file uploads, no push/email notifications, no websockets, no UI translation layers.
- **Allowed Stack Enforced**:
  - Python 3.12
  - FastAPI + SQLModel + Alembic + psycopg
  - Jinja2 + Pico.css + HTMX 1.9.12 (vendored, eval disabled)
  - pytest + pytest-playwright + freezegun + ruff
  - Docker + Docker Compose + GitHub Actions

---

## 3. Known Limitations (Documented in README & DECISIONS)

1. **No Student Accounts**: Public visitors view notice boards, routine, and exam schedules anonymously; only faculty/administrators have authenticated accounts.
2. **External Links Only**: Notices support external secure web links (`http`/`https`); attachments are not uploaded directly to application disk.
3. **Single Term Calendar Window**: `.ics` calendar generation calculates weekly recurring class schedules across the configured semester term window (`TERM_START` to `TERM_END`).

---

## 4. Remaining Manual Steps for User

1. **Deploy to Render (Optional)**: Follow [`DEPLOY.md`](DEPLOY.md) using the included `render.yaml` blueprint.
2. **Run Smoke Test against Live URL**: Once deployed, run `./scripts/smoke_test.sh <LIVE_URL>` to verify production configuration.
3. **Provision First Production Admin**: Log into Render Shell and execute `python -m app.cli create-admin`.
