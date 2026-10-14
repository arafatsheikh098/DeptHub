# need_fix — depthub

Security review 2026-10-14. Scope: security + real correctness bugs.
Full cross-project context: `../SECURITY_REVIEW.md`.

## Status: All 4 findings resolved and verified

### Verified: F1 — login lockout bypassable via X-Forwarded-For — HIGH
- `app/rate_limit.py`: Added `MAX_FAILED_ATTEMPTS_PER_EMAIL = 10`, counting failures per email across all source IPs, alongside existing per-(IP, email) cap of 5. Recorded as D005.
- Verified with regression test `test_login_rate_limit_not_bypassable_by_changing_ip` in `tests/test_auth.py`.

### Verified: F2 — open redirect on the login route — MEDIUM
- `app/routes/auth.py`: Added `is_safe_next()` (rejects absolute and protocol-relative targets), used at both redirect sites. Removed latent shadowing bug.
- Verified with regression test `test_login_next_param_rejects_offsite_redirect` in `tests/test_auth.py`.

### Verified: F3 — `/health` leaked internal error text — LOW/MEDIUM
- `app/main.py`: Returns `{"status": "unhealthy"}` without leaking database connection strings or internal exception details.
- Verified with regression test in `tests/test_health.py`.

### Resolved: F4 — dependencies unpinned — LOW
- `requirements.txt` and `requirements-dev.txt` pinned to exact installed versions (`pip freeze`).

### Secret Hygiene Check: PASS
- `git ls-files | grep -iE '(\.env$|\.db$|\.sqlite3?$|\.pem$|\.key$)'` returned 0 tracked secrets.
- `git log --all --oneline -- .env` returned 0 commits.

### Verification Evidence
- `pytest`: 92 passed, 1 skipped.
- `ruff check .`: All checks passed.
- `ruff format --check .`: 59 files formatted.
- Admin routes audit: All mutating admin endpoints consistently require `require_admin` and `verify_csrf`.
