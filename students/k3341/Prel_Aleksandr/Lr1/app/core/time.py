from datetime import datetime, timezone
from zoneinfo import ZoneInfo


MOSCOW = ZoneInfo("Europe/Moscow")


def utc_now() -> datetime:
    # Храним момент в UTC с явным поясом; московское время нужно только при отображении.
    return datetime.now(timezone.utc)


def as_moscow(value: datetime) -> datetime:
    # Без исходного пояса нельзя однозначно понять, какой момент времени нужно показать.
    if value.utcoffset() is None:
        raise ValueError("A timestamp must include its time zone")
    return value.astimezone(MOSCOW)
