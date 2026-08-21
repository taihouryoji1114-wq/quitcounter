from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


JAPAN = ZoneInfo("Asia/Tokyo")


def today_jst():
    """Return the business date in Japan, independent of the server region."""
    return datetime.now(JAPAN).date()


def now_jst():
    return datetime.now(JAPAN)


def operational_date_jst(cutoff_hour=2):
    """Return the store's operating date; a new day begins at the cutoff hour."""
    current = now_jst()
    if current.hour < cutoff_hour:
        current -= timedelta(days=1)
    return current.date()


def today_jst_string():
    return today_jst().isoformat()
