import os
from datetime import datetime
from zoneinfo import ZoneInfo


def now_local() -> datetime:
    return datetime.now(ZoneInfo(os.getenv("TIMEZONE", "America/Santiago"))).replace(tzinfo=None)
