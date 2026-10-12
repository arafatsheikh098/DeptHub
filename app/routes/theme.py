from fastapi import APIRouter, Query, Request, status
from fastapi.responses import RedirectResponse

from app.config import settings
from app.utils import THEME_COOKIE_NAME, VALID_THEMES

router = APIRouter(tags=["Theme"])


@router.get("/theme")
def set_theme(
    request: Request,
    set: str = Query(default="system", pattern="^(light|dark|system)$"),
    next: str | None = None,
):
    """Set or clear the user's color-theme preference cookie and redirect back.

    Uses a plain GET (not a state-changing POST) because the cookie stores a
    non-sensitive UI preference only; no CSRF protection is required.

    Values:
    - ``light``  → set ``data-theme="light"`` (Pico.css light scheme)
    - ``dark``   → set ``data-theme="dark"``  (Pico.css dark scheme)
    - ``system`` → clear the cookie, follow OS ``prefers-color-scheme``
    """
    target = next or "/"
    # Only allow same-site redirect targets to prevent open-redirect abuse.
    if not target.startswith("/") or target.startswith("//"):
        target = "/"

    response = RedirectResponse(url=target, status_code=status.HTTP_303_SEE_OTHER)

    if set == "system":
        # Clear the cookie by setting an expired date in the past.
        response.delete_cookie(THEME_COOKIE_NAME, path="/")
        return response

    if set in VALID_THEMES:
        response.set_cookie(
            key=THEME_COOKIE_NAME,
            value=set,
            max_age=31536000,  # 1 year
            path="/",
            secure=(settings.ENV == "production"),
            # Non-sensitive UI preference; readable by future JS if added.
            httponly=False,
            samesite="lax",
        )
    return response
