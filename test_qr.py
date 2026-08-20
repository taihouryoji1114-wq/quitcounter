import base64
import unittest

from core.qr import data_url


class QrCodeTest(unittest.TestCase):
    def test_store_login_qr_is_a_png_data_url(self):
        value = data_url("https://quitcounter.onrender.com/store-ops/login")
        prefix = "data:image/png;base64,"
        self.assertTrue(value.startswith(prefix))
        self.assertTrue(base64.b64decode(value[len(prefix):]).startswith(b"\x89PNG"))


if __name__ == "__main__":
    unittest.main()
