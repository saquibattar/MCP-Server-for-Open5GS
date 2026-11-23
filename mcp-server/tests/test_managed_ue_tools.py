import unittest
from unittest.mock import patch

from src.server import start_managed_ue_tool, stop_managed_ue_tool


class ManagedUEToolValidationTests(unittest.TestCase):
    @patch("src.server.fetch_subscriber_profile")
    @patch("src.server.create_managed_ue")
    def test_start_rejects_invalid_imsi_without_side_effects(
        self, create_ue, fetch_profile
    ):
        for imsi in ("bad-imsi", "1234", "1234567890123456", ""):
            with self.subTest(imsi=imsi):
                result = start_managed_ue_tool(imsi)
                self.assertFalse(result["success"])
                self.assertIn("IMSI", result["error"])

        fetch_profile.assert_not_called()
        create_ue.assert_not_called()

    @patch("src.server.stop_managed_ue")
    def test_stop_rejects_invalid_imsi_without_side_effects(self, stop_ue):
        for imsi in ("bad-imsi", "1234", "1234567890123456", ""):
            with self.subTest(imsi=imsi):
                result = stop_managed_ue_tool(imsi)
                self.assertFalse(result["success"])
                self.assertIn("IMSI", result["error"])

        stop_ue.assert_not_called()


if __name__ == "__main__":
    unittest.main()
