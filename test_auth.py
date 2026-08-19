import os
import unittest
from unittest.mock import patch

from core.auth import ROLE_PERMISSIONS, authenticate_pin, verify_pin


class AuthConfigurationTest(unittest.TestCase):
    def test_full_width_and_half_width_digits_match(self):
        with patch.dict(os.environ, {"HABITORY_PIN": "１２３４"}, clear=True):
            self.assertTrue(verify_pin("1234"))
            self.assertTrue(verify_pin(" １２３４ "))

    def test_wrong_pin_is_rejected(self):
        with patch.dict(os.environ, {"HABITORY_PIN": "1234"}, clear=True):
            self.assertFalse(verify_pin("1235"))

    def test_legacy_pin_remains_owner_pin(self):
        with patch.dict("os.environ", {"HABITORY_PIN": "１２３４"}, clear=True):
            account = authenticate_pin("1234", "portal")
        self.assertEqual(account["role"], "owner")

    def test_staff_pin_only_opens_store_operations(self):
        with patch.dict("os.environ", {"RBASE_STAFF_PIN": "5678"}, clear=True):
            self.assertEqual(authenticate_pin("5678", "store_ops")["role"], "staff")
            self.assertIsNone(authenticate_pin("5678", "portal"))
            self.assertIsNone(authenticate_pin("5678", "future_financials"))

    def test_only_owner_can_open_schedule_and_portal(self):
        self.assertIn("schedule", ROLE_PERMISSIONS["owner"])
        self.assertNotIn("schedule", ROLE_PERMISSIONS["partner"])
        self.assertNotIn("portal", ROLE_PERMISSIONS["staff"])


if __name__ == "__main__":
    unittest.main()
