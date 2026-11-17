"""clock.py: the one place the rig reads the wall clock where liveness matters.
AGE_NOW (ISO-8601 timestamp, e.g. 2026-11-12T09:00:00+00:00) freezes time for tests.
A naive AGE_NOW is taken as UTC."""
import datetime as _dt
import os


def now():
    """Timezone-aware datetime: AGE_NOW if set, else the real UTC time."""
    raw = os.environ.get("AGE_NOW")
    if raw:
        t = _dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return t if t.tzinfo else t.replace(tzinfo=_dt.timezone.utc)
    return _dt.datetime.now(_dt.timezone.utc)


def today():
    """Date of now() in UTC."""
    return now().astimezone(_dt.timezone.utc).date()
