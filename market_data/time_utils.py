from datetime import datetime, timezone


def datetime_to_milliseconds(value: datetime) -> int:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Time must include a timezone.")

    return int(value.timestamp() * 1000)


def milliseconds_to_datetime(value: int) -> datetime:
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
