import os
import socket
import threading
import time
import urllib.request

import pytest
import uvicorn
from playwright.sync_api import sync_playwright
from sqlmodel import Session

from app.database import engine, init_db
from app.main import create_app
from app.seed import seed_database


def _has_browser() -> bool:
    try:
        with sync_playwright() as p:
            exe = p.chromium.executable_path
            return bool(exe and os.path.exists(exe))
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _has_browser(),
    reason="Playwright chromium not installed (run 'playwright install chromium')",
)


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_server():
    """Spin up a live server on an ephemeral port seeded with demo data."""
    init_db()
    with Session(engine) as session:
        seed_database(session)

    port = get_free_port()
    config = uvicorn.Config(
        create_app(), host="127.0.0.1", port=port, log_level="error"
    )
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()

    base_url = f"http://127.0.0.1:{port}"
    # Wait for server health
    ready = False
    for _ in range(50):
        try:
            with urllib.request.urlopen(f"{base_url}/health") as resp:
                if resp.status == 200:
                    ready = True
                    break
        except Exception:
            time.sleep(0.08)

    assert ready, "Live test server failed to start"
    yield base_url

    server.should_exit = True
    t.join(timeout=2)


def test_public_visitor_flow_and_zero_csp_errors(live_server):
    """G6: Public visitor browsing flow and zero CSP console error validation."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        console_errors = []
        page.on(
            "console",
            lambda msg: (
                console_errors.append(msg.text) if msg.type == "error" else None
            ),
        )

        # 1. Notice Board
        page.goto(f"{live_server}/")
        assert "Notice Board" in page.title()
        assert page.locator("article").count() > 0

        # Search for notice
        page.fill("#search-input", "Programming")
        page.click("#filter-submit-btn")
        page.wait_for_load_state("networkidle")
        assert "Programming" in page.content()

        # 2. Routine Grid
        page.goto(f"{live_server}/routine")
        assert "Weekly Class Routine" in page.content()
        assert page.locator(".weekly-routine-grid").count() > 0

        # 3. Today's Schedule
        page.goto(f"{live_server}/today")
        assert "Today's Class Schedule" in page.content()

        # 4. Exam Schedule
        page.goto(f"{live_server}/exams")
        assert "Examination Schedule" in page.content()
        assert page.locator("#exams-list article").count() > 0

        # Verify zero CSP violations in console
        csp_errors = [
            e for e in console_errors if "Content Security Policy" in e or "CSP" in e
        ]
        assert len(csp_errors) == 0, f"CSP errors found: {csp_errors}"

        # 5. Theme toggle: clicking Dark link stays on the same path and applies
        #    data-theme="dark" to <html>, with no CSP console errors.
        page.goto(f"{live_server}/")
        assert page.locator("#theme-dark").count() == 1
        page.click("#theme-dark")
        # Toggle is a plain GET, so we land back on /
        assert 'data-theme="dark"' in page.content()
        csp_errors = [
            e for e in console_errors if "Content Security Policy" in e or "CSP" in e
        ]
        assert len(csp_errors) == 0, f"CSP errors after theme toggle: {csp_errors}"

        browser.close()


def test_no_horizontal_scroll_on_mobile_375px(live_server):
    """A3: Guarantee no horizontal scroll at 375px viewport on every public page."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 375, "height": 667})
        page = context.new_page()

        pages_to_check = ["/", "/routine", "/today", "/exams", "/auth/login"]
        for path in pages_to_check:
            page.goto(f"{live_server}{path}")
            page.wait_for_load_state("networkidle")

            # Check if document scrollWidth exceeds clientWidth
            has_horizontal_overflow = page.evaluate(
                "() => document.documentElement.scrollWidth > "
                "document.documentElement.clientWidth"
            )
            assert not has_horizontal_overflow, (
                f"Horizontal scroll detected on {path} at 375px viewport"
            )

        browser.close()


def test_javascript_disabled_flow(live_server):
    """G4: Verify application functionality when JavaScript is completely disabled."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # JavaScript explicitly disabled
        context = browser.new_context(java_script_enabled=False)
        page = context.new_page()

        # 1. Notice Board filter works via standard HTTP form submit
        page.goto(f"{live_server}/")
        page.fill("#search-input", "Scholarship")
        page.click("#filter-submit-btn")
        assert "Scholarship" in page.content()

        # 2. Routine batch selector submits without JS
        page.goto(f"{live_server}/routine")
        page.select_option("#batch_id", label="21-22 Session")
        # In noscript, click view routine button
        page.click("button:has-text('View Routine')")
        assert "21-22 Session" in page.content()

        # 3. Exams page submits without JS
        page.goto(f"{live_server}/exams")
        page.check("#show_past")
        page.click("button:has-text('Apply')")
        assert "Examination Schedule" in page.content()

        # 4. Theme toggle works via plain link navigation (no JS).
        page.goto(f"{live_server}/")
        # No data-theme on first visit (default = follow system)
        assert "data-theme=" not in page.content().split(">", 1)[0]
        # Click "Dark" toggle (a plain <a> link)
        page.click("#theme-dark")
        # Now the page should be on /, with data-theme="dark" on <html>
        assert 'data-theme="dark"' in page.content()
        # And the system toggle is NOT marked active
        dark_line = next(
            ln for ln in page.content().splitlines() if 'id="theme-dark"' in ln
        )
        assert 'aria-current="true"' in dark_line

        browser.close()


def test_admin_flow_and_conflict_detection(live_server):
    """G5: Admin login, notice creation, slot conflict detection, and audit trail."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # 1. Admin login
        page.goto(f"{live_server}/auth/login?next=/admin/notices")
        page.fill("#email", "admin@dept.local")
        page.fill("#password", "AdminPass123!")
        page.click("#login-submit-btn")
        page.wait_for_load_state("networkidle")
        assert "/admin/notices" in page.url

        # 2. Create Notice
        page.goto(f"{live_server}/admin/notices/new")
        page.fill("#title", "Playwright Automation Notice")
        page.fill("#body", "Created via automated end-to-end test.")
        page.select_option("#category", label="Event")
        page.click("#btn-submit")
        page.wait_for_load_state("networkidle")

        # Verify notice exists on admin list and public board
        page.goto(f"{live_server}/")
        assert "Playwright Automation Notice" in page.content()

        # 3. Routine Conflict Detection
        page.goto(f"{live_server}/admin/routine/new")
        # Try scheduling a slot that overlaps Room 301 on Monday (existing: 09:00-10:30)
        page.select_option("#batch_id", label="21-22 Session")
        page.select_option("#weekday", label="Monday")
        page.fill("#start_time", "09:30")
        page.fill("#end_time", "11:00")
        page.fill("#course_code", "CONFLICT-101")
        page.fill("#course_title", "Conflicting Class")
        page.fill("#teacher", "Dr. Conflict")
        page.fill("#room", "Room 301")  # Same room occupied by Dr. Codd
        page.click("#btn-submit")
        page.wait_for_load_state("networkidle")

        # Conflict error message must be shown
        assert "conflict" in page.content().lower()

        # 4. Audit Trail inspection
        page.goto(f"{live_server}/admin/audit")
        assert "Administrative Audit Trail" in page.content()
        assert "Playwright Automation Notice" in page.content()
        assert "admin@dept.local" in page.content()

        browser.close()
