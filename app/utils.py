from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import settings


def format_dt(dt: datetime | None, fmt: str = "%b %d, %Y %I:%M %p") -> str:
    """Format UTC datetime into configured TIMEZONE."""
    if dt is None:
        return ""
    try:
        tz = ZoneInfo(settings.TIMEZONE)
        if dt.tzinfo is None:
            # Assume UTC if naive
            from datetime import UTC

            dt = dt.replace(tzinfo=UTC)
        local_dt = dt.astimezone(tz)
        return local_dt.strftime(fmt)
    except Exception:  # noqa: BLE001
        return dt.strftime(fmt)


def is_safe_external_url(url: str | None) -> bool:
    """Validate external link scheme is strictly http or https."""
    if not url:
        return True
    trimmed = url.strip().lower()
    return trimmed.startswith("http://") or trimmed.startswith("https://")
