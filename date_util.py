from datetime import datetime, timezone


def datetime_to_int(d: datetime | None = None):
    # +2082844800 to convert Unix epoch (Jan 1 1970) to Mac epoch (Jan 1 1904)
    if d is None:
        d = datetime.now(timezone.utc)
    return int(d.timestamp()) + 2082844800


def int_to_datetime(i: int):
    i -= 2082844800
    return datetime.fromtimestamp(i, timezone.utc)
