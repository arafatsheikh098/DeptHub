import re

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.auth import get_password_hash
from app.main import app
from app.models.user import User


def get_state_changing_routes(router_or_app=None, prefix=""):
    if router_or_app is None:
        router_or_app = app
    results = []
    routes = getattr(router_or_app, "routes", [])
    for r in routes:
        if hasattr(r, "methods") and hasattr(r, "path"):
            for m in r.methods:
                if m in {"POST", "PUT", "PATCH", "DELETE"}:
                    path = prefix + r.path
                    results.append((path, m))
        elif hasattr(r, "original_router"):
            p = (
                getattr(r.include_context, "prefix", "")
                if hasattr(r, "include_context")
                else ""
            )
            results.extend(
                get_state_changing_routes(r.original_router, prefix=prefix + p)
            )
        elif hasattr(r, "routes"):
            results.extend(get_state_changing_routes(r, prefix=prefix))
    return sorted(list(set(results)))


STATE_CHANGING_ROUTES = get_state_changing_routes()


@pytest.mark.parametrize("path,method", STATE_CHANGING_ROUTES)
def test_state_changing_routes_reject_no_session_or_no_csrf(
    path: str, method: str, client: TestClient, session: Session
):
    # Setup test admin user
    admin_user = User(
        email="csrf_admin@example.com",
        password_hash=get_password_hash("Password123!"),
    )
    session.add(admin_user)
    session.commit()

    # Resolve any path parameters to dummy IDs e.g. {id} -> 1
    test_path = path.replace("{id}", "1").replace("{batch_id}", "1")

    # 1. Test without session: must reject with 401, 303 (redirect to login), or 403
    unauth_client = TestClient(app)
    resp_no_session = unauth_client.request(method, test_path, follow_redirects=False)
    assert resp_no_session.status_code in {
        401,
        403,
        303,
        307,
    }, f"Route {method} {test_path} without session gave {resp_no_session.status_code}"

    # 2. Test with admin session but MISSING / INVALID CSRF token: must return 403
    auth_client = TestClient(app)
    resp_login_page = auth_client.get("/auth/login")

    match = re.search(r'name="csrf_token" value="([^"]+)"', resp_login_page.text)
    csrf_token = match.group(1) if match else "dummy"

    # Login
    auth_client.post(
        "/auth/login",
        data={
            "email": "csrf_admin@example.com",
            "password": "Password123!",
            "csrf_token": csrf_token,
        },
    )

    # Now make request with bad/missing CSRF token
    resp_bad_csrf = auth_client.request(
        method,
        test_path,
        data={"csrf_token": "invalid_token_123"},
        headers={"X-CSRF-Token": "invalid_token_123"},
        follow_redirects=False,
    )
    msg = f"{method} {test_path} bad CSRF gave {resp_bad_csrf.status_code}"
    assert resp_bad_csrf.status_code == 403, msg
