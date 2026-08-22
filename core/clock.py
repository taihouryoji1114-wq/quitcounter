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


def store_service_period_jst():
    """Return the active restaurant service. Dinner starts at 15:30 JST."""
    current = now_jst()
    return "lunch" if (current.hour, current.minute) < (15, 30) else "dinner"


def today_jst_string():
    """Return Habitory's operating date; daily records reset at 02:00 JST."""
    return operational_date_jst().isoformat()
