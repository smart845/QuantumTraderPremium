
from datetime import datetime, timezone

def utcnow():
    return datetime.now(tz=timezone.utc)

def ensure_utc(dt: datetime):
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
