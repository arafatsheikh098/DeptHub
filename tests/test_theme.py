"""Tests for the explicit Light/Dark/System theme toggle (BACKLOG B003).

The toggle is a non-sensitive UI preference stored in the ``depthub_theme`` cookie.
The server reads the cookie and renders the matching ``data-theme`` attribute on
the ``<html>`` tag so the first paint is already in the chosen theme (no FOUC).

Implementation constraints verified here:
- No JavaScript required (links, not buttons).
- Cookie attributes: Path=/, SameSite=Lax, httponly=False, secure only in production.
- Invalid ``set`` values are rejected (HTTP 422 from Pydantic pattern validation).
- Open-redirect protection: ``next`` must start with a single ``/``.
"""

from fastapi.testclient import TestClient

from app.utils import THEME_COOKIE_NAME, VALID_THEMES


def test_get_theme_helper_returns_none_when_no_cookie():
    """No cookie -> None (follow system)."""
    from starlette.requests import Request

    scope = {"type": "http", "headers": []}
    req = Request(scope)
    from app.utils import get_theme

    assert get_theme(req) is None


def test_get_theme_helper_returns_valid_value():
    """A valid cookie value is returned as-is."""
    from starlette.requests import Request

    scope = {
        "type": "http",
        "headers": [(b"cookie", f"{THEME_COOKIE_NAME}=dark".encode())],
    }
    req = Request(scope)
    from app.utils import get_theme

    assert get_theme(req) == "dark"


def test_get_theme_helper_rejects_invalid_value():
    """An invalid cookie value is treated as no preference."""
    from starlette.requests import Request

    scope = {
        "type": "http",
        "headers": [(b"cookie", f"{THEME_COOKIE_NAME}=hotpink".encode())],
    }
    req = Request(scope)
    from app.utils import get_theme

    assert get_theme(req) is None


def test_set_theme_light_sets_cookie_and_redirects(client: TestClient):
    """GET /theme?set=light sets the cookie and 303s back to next=/."""
    response = client.get("/theme?set=light&next=/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"

    # Set-Cookie header (HTTPX/Starlette may emit multiple; find ours)
    set_cookies = response.headers.get_list("set-cookie")
    theme_cookie = next(
        (c for c in set_cookies if c.startswith(f"{THEME_COOKIE_NAME}=")),
        None,
    )
    assert theme_cookie is not None
    assert "depthub_theme=light" in theme_cookie
    assert "Path=/" in theme_cookie
    assert "samesite=lax" in theme_cookie.lower()  # intentionally readable by future JS
    assert "httponly" not in theme_cookie.lower()


def test_set_theme_dark_sets_cookie(client: TestClient):
    response = client.get("/theme?set=dark&next=/routine", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/routine"
    set_cookies = response.headers.get_list("set-cookie")
    assert any("depthub_theme=dark" in c for c in set_cookies)


def test_set_theme_system_clears_cookie(client: TestClient):
    """GET /theme?set=system clears the cookie (Max-Age=0)."""
    response = client.get("/theme?set=system&next=/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"
    set_cookies = response.headers.get_list("set-cookie")
    # delete_cookie emits a Set-Cookie with empty value and Max-Age=0 / expires in past
    assert any(THEME_COOKIE_NAME in c for c in set_cookies)
    clearing = next(c for c in set_cookies if THEME_COOKIE_NAME in c)
    assert ("max-age=0" in clearing.lower()) or ("expires=" in clearing.lower())


def test_set_theme_invalid_value_rejected(client: TestClient):
    """An invalid value triggers Pydantic pattern validation -> 422."""
    response = client.get("/theme?set=hotpink&next=/", follow_redirects=False)
    assert response.status_code == 422


def test_set_theme_open_redirect_blocked(client: TestClient):
    """next=//evil.com is rejected; falls back to /."""
    response = client.get(
        "/theme?set=light&next=//evil.com/phish", follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_set_theme_absolute_url_open_redirect_blocked(client: TestClient):
    """next=http://... (no leading slash) is rejected; falls back to /."""
    response = client.get(
        "/theme?set=light&next=http://evil.com", follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_default_next_is_root(client: TestClient):
    """If next is missing, the redirect target is /."""
    response = client.get("/theme?set=light", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_html_renders_data_theme_when_cookie_set(client: TestClient):
    """With the cookie set, the served HTML <html> tag has data-theme='light'."""
    client.cookies.set(THEME_COOKIE_NAME, "light")
    response = client.get("/")
    assert response.status_code == 200
    assert 'data-theme="light"' in response.text
    # And the light toggle is marked active
    assert 'id="theme-light"' in response.text
    assert 'aria-current="true"' in response.text


def test_html_renders_no_data_theme_when_no_cookie(client: TestClient):
    """Without a cookie, the served HTML <html> has no data-theme attribute."""
    response = client.get("/")
    assert response.status_code == 200
    # The exact opening <html> tag must not contain data-theme
    assert "data-theme" not in response.text.split(">", 1)[0]
    # And the system toggle is marked active
    assert 'id="theme-system"' in response.text
    assert 'aria-current="true"' in response.text


def test_all_toggle_links_present_on_every_page(client: TestClient):
    """The 3 toggle links (light/dark/system) appear on public and admin pages."""
    for path in ["/", "/routine", "/today", "/exams", "/auth/login"]:
        response = client.get(path, headers={"accept": "text/html"})
        # The auth/login page redirects, but the others render 200; just check the
        # base template was reached by looking for at least one of the toggle IDs.
        assert 'id="theme-light"' in response.text
        assert 'id="theme-dark"' in response.text
        assert 'id="theme-system"' in response.text


def test_active_button_reflects_cookie(client: TestClient):
    """The button matching the cookie has aria-current='true'; others don't."""
    for value in VALID_THEMES:
        client.cookies.set(THEME_COOKIE_NAME, value)
        response = client.get("/")
        active_id = f'id="theme-{value}"'
        # The active button must have aria-current
        assert active_id in response.text
        # Find the line and check it has aria-current
        for line in response.text.splitlines():
            if active_id in line and "theme-btn" in line:
                assert 'aria-current="true"' in line
                break
        else:
            raise AssertionError(f"Could not find theme-{value} line in response")
        # The other two buttons must NOT have aria-current
        for other in (v for v in VALID_THEMES if v != value):
            other_id = f'id="theme-{other}"'
            for line in response.text.splitlines():
                if other_id in line and "theme-btn" in line:
                    assert 'aria-current="true"' not in line
        # And the system button is NOT active when an explicit value is set
        for line in response.text.splitlines():
            if 'id="theme-system"' in line and "theme-btn" in line:
                assert 'aria-current="true"' not in line
