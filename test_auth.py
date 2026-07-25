import unittest
from unittest.mock import patch

from core.auth import verify_pin


class PinAuthenticationTest(unittest.TestCase):
    def test_pin_must_match_configured_secret(self):
        with patch.dict("os.environ", {"HABITORY_PIN": "2468"}):
            self.assertTrue(verify_pin("2468"))
            self.assertFalse(verify_pin("0000"))

    def test_missing_pin_never_authenticates(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertFalse(verify_pin(""))
            self.assertFalse(verify_pin("2468"))


if __name__ == "__main__":
    unittest.main()
