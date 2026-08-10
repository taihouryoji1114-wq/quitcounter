import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from core.data import DataManager
from core.reading import ReadingManager


JAPAN = ZoneInfo("Asia/Tokyo")


class ReadingManagerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.manager = DataManager(Path(self.temp_dir.name) / "data.json")
        self.reading = ReadingManager(self.manager)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_start_and_stop_accumulate_daily_reading_time(self):
        started = datetime(2026, 7, 29, 20, 0, tzinfo=JAPAN)
        self.reading.start("user1", started)
        session = self.reading.stop("user1", started + timedelta(minutes=25))
        self.assertEqual(session["seconds"], 1500)
        self.assertEqual(
            self.reading.total_seconds("2026-07-29", "user1"), 1500
        )

    def test_active_timer_is_saved_and_included(self):
        started = datetime(2026, 7, 29, 20, 0, tzinfo=JAPAN)
        self.reading.start("user1", started)
        self.assertEqual(
            self.reading.total_seconds(
                "2026-07-29", "user1", now=started + timedelta(minutes=5)
            ),
            300,
        )
        with self.assertRaisesRegex(ValueError, "すでに読書中"):
            self.reading.start("user1", started)

    def test_multiple_sessions_and_goal_are_user_scoped(self):
        started = datetime(2026, 7, 29, 8, 0, tzinfo=JAPAN)
        for offset in (0, 60):
            session_start = started + timedelta(minutes=offset)
            self.reading.start("user1", session_start)
            self.reading.stop("user1", session_start + timedelta(minutes=15))
        self.reading.set_goal_minutes(30, "user1")
        self.assertEqual(self.reading.total_seconds("2026-07-29", "user1"), 1800)
        self.assertEqual(self.reading.get_goal_minutes("user1"), 30)
        self.assertIsNone(self.reading.get_goal_minutes("user2"))

    def test_session_crossing_midnight_is_split_between_dates(self):
        started = datetime(2026, 7, 29, 23, 55, tzinfo=JAPAN)
        self.reading.start("user1", started)
        self.reading.stop("user1", started + timedelta(minutes=15))
        self.assertEqual(self.reading.total_seconds("2026-07-29", "user1"), 300)
        self.assertEqual(self.reading.total_seconds("2026-07-30", "user1"), 600)

    def test_monthly_summary_totals_time_and_reading_days(self):
        first = datetime(2026, 7, 1, 20, 0, tzinfo=JAPAN)
        second = datetime(2026, 7, 3, 20, 0, tzinfo=JAPAN)
        for started, minutes in ((first, 20), (second, 40)):
            self.reading.start("user1", started)
            self.reading.stop("user1", started + timedelta(minutes=minutes))
        summary = self.reading.monthly_summary("2026-07", "user1")
        self.assertEqual(summary["seconds"], 3600)
        self.assertEqual(summary["days"], 2)


if __name__ == "__main__":
    unittest.main()
