import os
import unittest
from unittest.mock import patch

from core.auth import verify_pin


class AuthTest(unittest.TestCase):
    def test_full_width_and_half_width_digits_match(self):
        with patch.dict(os.environ, {"HABITORY_PIN": "１２３４"}):
            self.assertTrue(verify_pin("1234"))
            self.assertTrue(verify_pin(" １２３４ "))

    def test_wrong_pin_is_rejected(self):
        with patch.dict(os.environ, {"HABITORY_PIN": "1234"}):
            self.assertFalse(verify_pin("1235"))


if __name__ == "__main__":
    unittest.main()
