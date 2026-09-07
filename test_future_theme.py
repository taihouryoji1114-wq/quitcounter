import unittest
from pathlib import Path

from core.future_theme import (
    DEFAULT_THEME,
    STORAGE_KEY,
    normalize_theme,
    theme_controls_html,
    theme_head_html,
)


class FutureThemeTest(unittest.TestCase):
    def test_theme_codes_are_case_insensitive(self):
        self.assertEqual(normalize_theme("NORMAL"), "normal")
        self.assertEqual(normalize_theme(" godot "), "godot")

    def test_unknown_or_broken_theme_falls_back_to_normal(self):
        self.assertEqual(normalize_theme("cyber"), DEFAULT_THEME)
        self.assertEqual(normalize_theme(None), DEFAULT_THEME)
        self.assertEqual(normalize_theme({"broken": True}), DEFAULT_THEME)

    def test_bootstrap_is_visual_only_local_storage(self):
        html = theme_head_html()
        self.assertIn(STORAGE_KEY, html)
        self.assertIn("localStorage", html)
        self.assertIn("dataset.miraiTheme", html)
        self.assertNotIn("business_sales", html)
        self.assertNotIn("fetch(", html)

    def test_hidden_console_supports_apply_cancel_and_invalid_code(self):
        html = theme_controls_html()
        self.assertIn("data-theme-close", html)
        self.assertIn("mirai-theme-apply", html)
        self.assertIn("使用できないテーマコードです", html)
        self.assertIn("taps >= 5", html)

    def test_godot_theme_is_scoped_and_uses_no_heavy_media(self):
        css = (Path(__file__).parent / "static" / "mirai_kessan_themes.css").read_text()
        self.assertIn('html[data-mirai-theme="godot"]', css)
        self.assertIn("@media (max-width: 520px)", css)
        self.assertIn("prefers-reduced-motion", css)
        self.assertNotIn(".mp4", css)
        self.assertNotIn(".png", css)


if __name__ == "__main__":
    unittest.main()
