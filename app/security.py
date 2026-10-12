import hmac
import secrets

from fastapi import HTTPException, Request, status


def get_csrf_token(request: Request) -> str:
    """Retrieve or generate a CSRF token stored in the user's signed session."""
    token = request.session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


async def verify_csrf(request: Request) -> None:
    """Verify CSRF token for state-changing HTTP requests.

    Accepts the token either in X-CSRF-Token header or csrf_token form field.
    """
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return

    expected = request.session.get("csrf_token")
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing or session expired",
        )

    # 1. Header (standard or HTMX)
    token = request.headers.get("X-CSRF-Token") or request.headers.get("x-csrf-token")

    # 2. Form field
    if not token:
        content_type = request.headers.get("content-type", "")
        if (
            "application/x-www-form-urlencoded" in content_type
            or "multipart/form-data" in content_type
        ):
            try:
                form = await request.form()
                token = form.get("csrf_token")
            except Exception:  # noqa: BLE001
                token = None

    if not token or not hmac.compare_digest(str(expected), str(token)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing CSRF token",
        )


class SecurityHeadersMiddleware:
    """Pure ASGI middleware adding standard security headers to every response."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                sec_headers = [
                    (
                        b"content-security-policy",
                        (
                            b"default-src 'self'; "
                            b"script-src 'self'; "
                            b"style-src 'self' 'unsafe-inline'; "
                            b"img-src 'self' data:; "
                            b"font-src 'self'; "
                            b"frame-ancestors 'none'; "
                            b"base-uri 'self'; "
                            b"form-action 'self';"
                        ),
                    ),
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin"),
                    (b"x-frame-options", b"DENY"),
                    (
                        b"permissions-policy",
                        b"geolocation=(), camera=(), microphone=()",
                    ),
                ]
                headers.extend(sec_headers)
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)
