import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from core.clock import operational_date_jst, today_jst_string


class OperatingDateTest(unittest.TestCase):
    def test_before_two_am_belongs_to_previous_day(self):
        current = datetime(2026, 8, 21, 1, 59, tzinfo=ZoneInfo("Asia/Tokyo"))
        with patch("core.clock.now_jst", return_value=current):
            self.assertEqual(operational_date_jst().isoformat(), "2026-08-20")
            self.assertEqual(today_jst_string(), "2026-08-20")

    def test_two_am_starts_new_day(self):
        current = datetime(2026, 8, 21, 2, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
        with patch("core.clock.now_jst", return_value=current):
            self.assertEqual(operational_date_jst().isoformat(), "2026-08-21")


if __name__ == "__main__":
    unittest.main()
