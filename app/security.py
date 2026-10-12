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
