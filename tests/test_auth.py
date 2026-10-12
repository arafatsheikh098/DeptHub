from datetime import timedelta

from fastapi.testclient import TestClient
from freezegun import freeze_time
from sqlmodel import Session, select

from app.auth import get_password_hash
from app.cli import create_admin
from app.models.user import User


def test_login_wrong_password_and_unknown_email_same_error(
    client: TestClient, session: Session
):
    # Create user
    user = User(
        email="realadmin@example.com",
        password_hash=get_password_hash("CorrectPassword123!"),
    )
    session.add(user)
    session.commit()

    # Get CSRF token
    resp_get = client.get("/auth/login")
    assert resp_get.status_code == 200
    import re

    token_match = re.search(r'name="csrf_token" value="([^"]+)"', resp_get.text)
    assert token_match, "CSRF token not found in form"
    csrf_token = token_match.group(1)

    # 1. Attempt with unknown email
    resp_unknown = client.post(
        "/auth/login",
        data={
            "email": "nonexistent@example.com",
            "password": "AnyPassword123!",
            "csrf_token": csrf_token,
        },
    )

    # 2. Attempt with real email, wrong password
    resp_wrong_pw = client.post(
        "/auth/login",
        data={
            "email": "realadmin@example.com",
            "password": "WrongPassword123!",
            "csrf_token": csrf_token,
        },
    )

    # Must produce the exact same status code and error message
    assert resp_unknown.status_code == 400
    assert resp_wrong_pw.status_code == 400
    assert "Invalid email or password" in resp_unknown.text
    assert "Invalid email or password" in resp_wrong_pw.text
    assert resp_unknown.template.name == resp_wrong_pw.template.name == "login.html"


def test_login_rate_limiting_triggers_and_resets(client: TestClient):
    with freeze_time("2026-10-12 12:00:00") as frozen_time:
        resp_get = client.get("/auth/login")
        import re

        csrf_token = re.search(
            r'name="csrf_token" value="([^"]+)"', resp_get.text
        ).group(1)

        email = "bruteforce@example.com"
        # 5 failed attempts allowed (returning 400)
        for i in range(5):
            resp = client.post(
                "/auth/login",
                data={
                    "email": email,
                    "password": f"wrong_{i}",
                    "csrf_token": csrf_token,
                },
            )
            assert resp.status_code == 400

        # 6th attempt must trigger 429
        resp_6 = client.post(
            "/auth/login",
            data={
                "email": email,
                "password": "wrong_6",
                "csrf_token": csrf_token,
            },
        )
        assert resp_6.status_code == 429
        assert "Too many failed login attempts" in resp_6.text

        # Advance time by 16 minutes (window is 15 minutes)
        frozen_time.tick(delta=timedelta(minutes=16))

        # Attempt should now not be blocked by 429
        resp_after_window = client.post(
            "/auth/login",
            data={
                "email": email,
                "password": "wrong_after",
                "csrf_token": csrf_token,
            },
        )
        assert resp_after_window.status_code == 400


def test_login_cookie_flags(client: TestClient, session: Session):
    user = User(
        email="cookieadmin@example.com",
        password_hash=get_password_hash("SecurePassword123!"),
    )
    session.add(user)
    session.commit()

    resp_get = client.get("/auth/login")
    import re

    csrf_token = re.search(r'name="csrf_token" value="([^"]+)"', resp_get.text).group(1)

    resp_login = client.post(
        "/auth/login",
        data={
            "email": "cookieadmin@example.com",
            "password": "SecurePassword123!",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )
    assert resp_login.status_code == 303

    # Check session cookie in response headers
    cookie_header = resp_login.headers.get("set-cookie", "")
    assert "depthub_session=" in cookie_header
    assert "HttpOnly" in cookie_header or "httponly" in cookie_header.lower()
    assert "SameSite=lax" in cookie_header or "samesite=lax" in cookie_header.lower()


def test_cli_create_admin(session: Session):
    create_admin(
        email="cliadmin@example.com",
        password="Clipassword123!",
        session=session,
    )
    user = session.exec(
        select(User).where(User.email == "cliadmin@example.com")
    ).first()
    assert user is not None
    assert user.email == "cliadmin@example.com"
