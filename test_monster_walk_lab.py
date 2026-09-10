import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent / "static" / "monster-walk-lab"


class MonsterWalkLabTest(unittest.TestCase):
    def test_battle_hit_has_no_yellow_sepia_effect(self):
        css = (ROOT / "style.css").read_text(encoding="utf-8")
        self.assertNotIn("sepia(1) saturate(5)", css)
        self.assertIn("grayscale(1)", css)

    def test_command_area_is_larger_than_previous_layout(self):
        css = (ROOT / "style.css").read_text(encoding="utf-8")
        self.assertIn("minmax(210px,34fr)", css)
        self.assertIn(".battle-command[hidden],.battle-moves[hidden]", css)

    def test_starting_town_has_walk_and_collision_system(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="town-map"', html)
        self.assertIn('id="town-hero"', html)
        self.assertIn("function townBlocked", script)
        self.assertIn("requestAnimationFrame(moveTown)", script)


if __name__ == "__main__":
    unittest.main()
