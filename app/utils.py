from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from app.config import settings

WEEKDAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


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


def get_current_local_date_and_weekday() -> tuple[date, str]:
    """Compute current date and weekday name in the configured TIMEZONE."""
    tz = ZoneInfo(settings.TIMEZONE)
    local_now = datetime.now(tz)
    return local_now.date(), local_now.strftime("%A")
