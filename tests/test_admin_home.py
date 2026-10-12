"""Tests for the /admin landing page (admin dashboard)."""

import re

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.auth import get_password_hash
from app.models.user import User


def _login_as_admin(client: TestClient, session: Session, email: str) -> None:
    """Create + log in a test admin user."""
    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        user = User(email=email, password_hash=get_password_hash("AdminPass123!"))
        session.add(user)
        session.commit()
    resp = client.get("/auth/login")
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', resp.text).group(1)
    client.post(
        "/auth/login",
        data={"email": email, "password": "AdminPass123!", "csrf_token": csrf},
    )


def test_admin_home_requires_authentication(client: TestClient):
    """Unauthenticated request redirects to login."""
    resp = client.get("/admin", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/auth/login")


def test_admin_home_returns_200_when_logged_in(client: TestClient, session: Session):
    _login_as_admin(client, session, "adminhome1@example.com")
    resp = client.get("/admin")
    assert resp.status_code == 200


def test_admin_home_links_to_all_sections(client: TestClient, session: Session):
    """Landing page must have cards linking to every admin section."""
    _login_as_admin(client, session, "adminhome2@example.com")
    resp = client.get("/admin")
    assert resp.status_code == 200
    body = resp.text
    for path in [
        "/admin/notices",
        "/admin/batches",
        "/admin/routine",
        "/admin/exams",
        "/admin/audit",
    ]:
        assert f'href="{path}"' in body, f"Missing link to {path}"


def test_admin_home_shows_counts(client: TestClient, session: Session):
    """Landing page must show record counts (at least 0) for each section."""
    _login_as_admin(client, session, "adminhome3@example.com")
    resp = client.get("/admin")
    body = resp.text
    # Each section's count line includes these words.
    assert "total" in body  # notices
    assert "batch" in body.lower()
    assert "slot" in body.lower()
    assert "exam" in body.lower()
    assert "entr" in body.lower()  # entries / entry


def test_admin_home_title_and_heading(client: TestClient, session: Session):
    _login_as_admin(client, session, "adminhome4@example.com")
    resp = client.get("/admin")
    assert resp.status_code == 200
    assert "Admin Dashboard" in resp.text


def test_top_nav_admin_link_points_to_admin_home(client: TestClient, session: Session):
    """The top-nav 'Admin' link should point to /admin (the landing page)."""
    _login_as_admin(client, session, "adminhome5@example.com")
    resp = client.get("/admin")
    # The base.html top-nav link with id="nav-admin" should point at /admin.
    # Attributes may appear in either order, so check both.
    assert re.search(r'<a\s+href="/admin"\s+id="nav-admin"', resp.text) or re.search(
        r'<a\s+id="nav-admin"\s+href="/admin"', resp.text
    )


def test_admin_home_html_request_for_redirect_preserves_next(
    client: TestClient,
):
    """An unauthenticated visit to /admin?anything should still go to login."""
    resp = client.get("/admin", follow_redirects=False)
    assert resp.status_code == 303
    assert "/auth/login" in resp.headers["location"]
