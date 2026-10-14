# BACKLOG

| ID | Idea | Why | Effort |
|---|---|---|---|
| B001 | Notice PDF / File Attachments | Allow administrators to attach circular PDFs to notices | Medium |
| B002 | Email Notification Digest | Enable students to subscribe for daily notice digest emails | Medium |
| ~~B003~~ | ~~Explicit Theme Toggle~~ | **Shipped 2026-10-13** — see `tests/test_theme.py` | ~~Low~~ |
| B004 | Multi-Semester Historical Archive | Archive older terms with readonly historical browse capability | Medium |
| B005 | Batch-restricted routine view | Limit routine/exam visibility to a user's own batch (requires student accounts, currently OUT OF SCOPE) | High |
| B006 | Trust X-Forwarded-For only from allowlisted proxies | `get_client_ip` accepts the header from any caller, so per-IP login throttling and audit attribution can be spoofed; honour `FORWARDED_ALLOW_IPS` instead (the email-wide cap in D005 already bounds brute force) | Low |
