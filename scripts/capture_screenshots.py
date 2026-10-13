"""Capture updated high-resolution screenshots for README documentation."""

import socket
import threading
import time
import urllib.request
from contextlib import closing
from pathlib import Path

import uvicorn
from playwright.sync_api import sync_playwright
from sqlmodel import Session

from app.database import engine, init_db
from app.main import create_app
from app.seed import seed_database


def get_free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main():
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)

    # Ensure DB is seeded
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

    # Wait for server
    for _ in range(50):
        try:
            with urllib.request.urlopen(f"{base_url}/health") as resp:
                if resp.status == 200:
                    break
        except Exception:
            time.sleep(0.1)

    print(f"Server started at {base_url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 1. Desktop Screenshots (1200x800)
        desktop_context = browser.new_context(
            viewport={"width": 1200, "height": 800},
            device_scale_factor=1,
        )

        # Notice Board
        page = desktop_context.new_page()
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")
        page.screenshot(path="docs/screenshot_notices.png")
        print("Captured docs/screenshot_notices.png")

        # Routine
        page.goto(f"{base_url}/routine")
        page.wait_for_load_state("networkidle")
        page.screenshot(path="docs/screenshot_routine.png")
        print("Captured docs/screenshot_routine.png")

        # Today
        page.goto(f"{base_url}/today")
        page.wait_for_load_state("networkidle")
        page.screenshot(path="docs/screenshot_today.png")
        print("Captured docs/screenshot_today.png")

        # Exams
        page.goto(f"{base_url}/exams")
        page.wait_for_load_state("networkidle")
        page.screenshot(path="docs/screenshot_exams.png")
        print("Captured docs/screenshot_exams.png")

        # Dark Mode
        page.goto(f"{base_url}/theme?set=dark&next=/")
        page.wait_for_load_state("networkidle")
        page.screenshot(path="docs/screenshot_dark.png")
        print("Captured docs/screenshot_dark.png")

        desktop_context.close()

        # 2. Mobile Screenshot (375x750)
        mobile_context = browser.new_context(
            viewport={"width": 375, "height": 750},
            device_scale_factor=1,
            is_mobile=True,
            has_touch=True,
        )
        mobile_page = mobile_context.new_page()
        mobile_page.goto(f"{base_url}/")
        mobile_page.wait_for_load_state("networkidle")
        mobile_page.screenshot(path="docs/screenshot_mobile.png")
        print("Captured docs/screenshot_mobile.png")

        mobile_context.close()
        browser.close()

    server.should_exit = True
    t.join(timeout=2)
    print("All screenshots updated successfully!")


if __name__ == "__main__":
    main()
