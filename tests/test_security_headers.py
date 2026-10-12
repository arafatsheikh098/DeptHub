from fastapi.testclient import TestClient


def test_security_headers_present_on_all_responses(client: TestClient):
    resp = client.get("/")
    assert resp.status_code == 200

    # 1. Content-Security-Policy
    csp = resp.headers.get("content-security-policy", "")
    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    # Script-src must NOT allow unsafe-inline
    assert "script-src 'self' 'unsafe-inline'" not in csp

    # 2. X-Content-Type-Options
    assert resp.headers.get("x-content-type-options") == "nosniff"

    # 3. Referrer-Policy
    assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    # 4. X-Frame-Options
    assert resp.headers.get("x-frame-options") == "DENY"

    # 5. Permissions-Policy
    assert "geolocation=()" in resp.headers.get("permissions-policy", "")


def test_custom_404_error_page_for_html_requests(client: TestClient):
    resp = client.get(
        "/nonexistent-page-that-does-not-exist", headers={"accept": "text/html"}
    )
    assert resp.status_code == 404
    assert "Page Not Found" in resp.text
    assert "404" in resp.text
