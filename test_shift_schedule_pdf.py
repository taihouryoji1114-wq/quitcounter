import tempfile
import unittest
from pathlib import Path

from core.shift_schedule_pdf import create_shift_schedule_pdf


class ShiftSchedulePdfTest(unittest.TestCase):
    def test_creates_landscape_shift_pdf(self):
        staff = ("店長", "スタッフA")
        plan = lambda lunch, dinner, cuts=None: {
            "lunch": lunch, "dinner": dinner, "time": "通し",
            "requested_type": "通し", "cut_meals": cuts or [],
        }
        result = {
            "period": {"year": 2026, "month": 9, "start": 1, "end": 1},
            "days": {"1": {"staff": {
                "店長": plan(True, True),
                "スタッフA": plan(False, True, ["L"]),
            }, "shortages": {"lunch": 0, "dinner": 0}}},
            "settings": {"manual_overrides": {"1": {"スタッフA": "ディナー"}}},
        }
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "shift.pdf"
            create_shift_schedule_pdf(output, result, staff)
            self.assertTrue(output.exists())
            self.assertGreater(output.stat().st_size, 1_000)


if __name__ == "__main__":
    unittest.main()
