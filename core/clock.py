from datetime import datetime
from zoneinfo import ZoneInfo


JAPAN = ZoneInfo("Asia/Tokyo")


def today_jst():
    """Return the business date in Japan, independent of the server region."""
    return datetime.now(JAPAN).date()


def now_jst():
    return datetime.now(JAPAN)


def today_jst_string():
    return today_jst().isoformat()
