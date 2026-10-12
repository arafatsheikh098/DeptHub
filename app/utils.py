from datetime import date, datetime, time
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from fastapi import Request

from app.config import settings

THEME_COOKIE_NAME = "depthub_theme"
VALID_THEMES = ("light", "dark")

# Hosts whose content we will render inline (in an iframe) when linked from a
# notice. Anything not in this set is shown as a clickable "External Link" only.
PREVIEW_ALLOWED_HOSTS = frozenset(
    {
        "docs.google.com",
        "drive.google.com",
        "www.dropbox.com",
        "dropbox.com",
        "onedrive.live.com",
        "1drv.ms",
        "www.youtube.com",
        "youtube.com",
        "youtu.be",
        "player.vimeo.com",
        "vimeo.com",
    }
)

WEEKDAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

WEEKDAY_CODES = {
    "Monday": "MO",
    "Tuesday": "TU",
    "Wednesday": "WE",
    "Thursday": "TH",
    "Friday": "FR",
    "Saturday": "SA",
    "Sunday": "SU",
}

WEEKDAY_NUMBERS = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}


def format_dt(dt: datetime | None, fmt: str = "%b %d, %Y %I:%M %p") -> str:
    """Format UTC datetime into configured TIMEZONE."""
    if dt is None:
        return ""
    try:
        tz = ZoneInfo(settings.TIMEZONE)
        if dt.tzinfo is None:
            from datetime import UTC

            dt = dt.replace(tzinfo=UTC)
        local_dt = dt.astimezone(tz)
        return local_dt.strftime(fmt)
    except Exception:  # noqa: BLE001
        return dt.strftime(fmt)


def format_time(t: time | None, fmt: str = "%I:%M %p") -> str:
    """Format time object to 12-hour format string."""
    if t is None:
        return ""
    return t.strftime(fmt).lstrip("0")


def format_date(d: date | None, fmt: str = "%b %d, %Y") -> str:
    """Format date object."""
    if d is None:
        return ""
    return d.strftime(fmt)


def is_safe_external_url(url: str | None) -> bool:
    """Validate external link scheme is strictly http or https."""
    if not url:
        return True
    trimmed = url.strip().lower()
    return trimmed.startswith("http://") or trimmed.startswith("https://")


def preview_host(url: str | None) -> str | None:
    """Return the host of the URL if it's in the inline-preview whitelist.

    Returns None if the URL is missing, malformed, or not in the whitelist.
    """
    if not url:
        return None
    try:
        host = (urlparse(url.strip()).hostname or "").lower()
    except ValueError:
        return None
    if host in PREVIEW_ALLOWED_HOSTS:
        return host
    return None


def embed_url(url: str | None) -> str | None:
    """Return a URL suitable for inline iframe embedding, or None.

    - For Google Docs/Drive ``/edit`` links, rewrites to ``/preview`` for a
      clean read-only view.
    - For YouTube ``watch?v=ID`` links, rewrites to ``embed/ID``.
    - For Vimeo ``vimeo.com/ID`` links, rewrites to ``player.vimeo.com/video/ID``.
    - For other whitelisted hosts, returns the URL unchanged.
    - Returns None if the host is not in the preview whitelist.
    """
    host = preview_host(url)
    if not host:
        return None
    parsed = urlparse(url.strip())

    # Google Docs / Drive: /edit or /view -> /preview
    if host in ("docs.google.com", "drive.google.com"):
        # Only the path; preserve any extra path segments after the doc id.
        # e.g. /document/d/ID/edit -> /document/d/ID/preview
        #      /file/d/ID/view    -> /file/d/ID/preview
        path = parsed.path
        if path.endswith("/edit") or path.endswith("/view"):
            path = path.rsplit("/", 1)[0] + "/preview"
            return f"{parsed.scheme}://{parsed.netloc}{path}"
        return url.strip()

    # YouTube watch?v=ID -> embed/ID
    if host in ("www.youtube.com", "youtube.com"):
        qs = dict(p.split("=", 1) for p in parsed.query.split("&") if "=" in p)
        vid = qs.get("v")
        if vid:
            return f"https://www.youtube.com/embed/{vid}"
        return url.strip()

    # youtu.be/ID -> embed/ID
    if host == "youtu.be":
        vid = parsed.path.lstrip("/").split("/")[0]
        if vid:
            return f"https://www.youtube.com/embed/{vid}"
        return url.strip()

    # vimeo.com/ID -> player.vimeo.com/video/ID
    if host == "vimeo.com":
        parts = [p for p in parsed.path.split("/") if p]
        if parts and parts[0].isdigit():
            return f"https://player.vimeo.com/video/{parts[0]}"
        return url.strip()

    return url.strip()


def get_current_local_date_and_weekday() -> tuple[date, str]:
    """Compute current date and weekday name in the configured TIMEZONE."""
    tz = ZoneInfo(settings.TIMEZONE)
    local_now = datetime.now(tz)
    return local_now.date(), local_now.strftime("%A")


def get_theme(request: Request) -> str | None:
    """Read and validate the user's theme preference from the cookie.

    Returns "light" or "dark" if the cookie is set to a valid value, otherwise
    ``None`` (meaning "follow system", which is Pico.css's default).
    """
    raw = request.cookies.get(THEME_COOKIE_NAME)
    if raw and raw in VALID_THEMES:
        return raw
    return None
