from datetime import UTC, datetime


def datetime_to_int(d: datetime | None = None):
    # +2082844800 to convert Unix epoch (1970-01-01T00:00Z) to Mac epoch (1904-01-01T00:00Z)
    if d is None:
        d = datetime.now(UTC)
    return int(d.timestamp()) + 2082844800


def int_to_datetime(i: int):
    i -= 2082844800
    return datetime.fromtimestamp(i, UTC)
