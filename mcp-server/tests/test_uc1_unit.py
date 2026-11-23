import unittest
from unittest.mock import MagicMock, patch
import os
import json
import requests

# Import the tools to be tested
# Since server.py is the entry point for tool logic, we test the tool functions there.
from src.server import (
    add_subscriber_tool,
    get_subscriber_tool,
    add_slice_tool,
    SubscriberRequest
)
from src.tools.slices import add_slice
from src.tools.subscribers import add_subscriber

class TestUC1Unit(unittest.TestCase):

    def setUp(self):
        # Save original environment variable
        self.orig_allow_creds = os.environ.get("OPEN5GS_ALLOW_CREDENTIAL_READ")
        os.environ["OPEN5GS_ALLOW_CREDENTIAL_READ"] = "false"

        # Mock constants for tests
        self.valid_imsi = "001010000000001"
        self.invalid_imsi = "abc123"
        self.mock_profile = {
            "imsi": self.valid_imsi,
            "security": {"amf": "8000", "k": "1234567890abcdef1234567890abcdef", "opc": "abcdef1234567890abcdef1234567890"},
            "slice": [
                {
                    "sst": 1,
                    "default_indicator": True,
                    "session": [{"name": "internet", "type": 3}]
                }
            ]
        }

    def tearDown(self):
        # Restore environment variable
        if self.orig_allow_creds is None:
            if "OPEN5GS_ALLOW_CREDENTIAL_READ" in os.environ:
                del os.environ["OPEN5GS_ALLOW_CREDENTIAL_READ"]
        else:
            os.environ["OPEN5GS_ALLOW_CREDENTIAL_READ"] = self.orig_allow_creds

    @patch('src.tools.subscribers.Open5GSClient')
    def test_add_subscriber_valid(self, mock_client_cls):
        # Setup: Mock subscriber does not exist, and add succeeds
        mock_client = mock_client_cls.return_value
        mock_client.list_subscribers.return_value = json.dumps([])
        mock_client.get_subscriber.return_value = json.dumps({"exists": False}) # This is a simplification

        # The add_subscriber_tool uses subscriber_exists(imsi) which calls get_subscriber
        # Actually, it calls subscriber_exists(imsi) which is in subscribers.py
        # Let's mock the tool-level dependencies more precisely.

        with patch('src.server.subscriber_exists') as mock_exists:
            mock_exists.return_value = {"exists": False}
            with patch('src.server.add_subscriber') as mock_add:
                mock_add.return_value = json.dumps({"status": "created"})

                result = add_subscriber_tool(imsi=self.valid_imsi)

                self.assertTrue(result["success"])
                self.assertEqual(result["status"], "provisioned")
                mock_add.assert_called_once()

    @patch('src.server.subscriber_exists')
    @patch('src.server.add_subscriber')
    def test_add_subscriber_duplicate(self, mock_add, mock_exists):
        # Setup: Subscriber already exists
        mock_exists.return_value = {"exists": True}

        result = add_subscriber_tool(imsi=self.valid_imsi)

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "already_exists")
        mock_add.assert_not_called()

    def test_add_subscriber_invalid_imsi(self):
        # Test validation logic in add_subscriber_tool
        result = add_subscriber_tool(imsi=self.invalid_imsi)

        self.assertFalse(result["success"])
        self.assertIn("IMSI must contain 5 to 15 digits", result["error"])

    @patch('src.server.get_subscriber')
    def test_credential_redaction(self, mock_get_sub):
        # Setup: Mock profile containing secrets
        mock_get_sub.return_value = json.dumps(self.mock_profile)

        # Test default behavior (redaction)
        request = SubscriberRequest(imsi=self.valid_imsi)
        result = get_subscriber_tool(request)

        self.assertIn("security", result)
        self.assertTrue(result["security"]["configured"])
        self.assertNotIn("k", result["security"])
        self.assertNotIn("opc", result["security"])

    @patch('src.server.get_subscriber')
    def test_credential_read_opt_in(self, mock_get_sub):
        # Setup: Enable credential read
        os.environ["OPEN5GS_ALLOW_CREDENTIAL_READ"] = "true"
        mock_get_sub.return_value = json.dumps(self.mock_profile)

        request = SubscriberRequest(imsi=self.valid_imsi)
        result = get_subscriber_tool(request)

        self.assertIn("k", result["security"])
        self.assertIn("opc", result["security"])
        self.assertEqual(result["security"]["k"], self.mock_profile["security"]["k"])

    @patch('src.server.add_subscriber')
    @patch('src.server.subscriber_exists')
    def test_default_slice_provisioning(self, mock_exists, mock_add):
        mock_exists.return_value = {"exists": False}
        mock_add.return_value = json.dumps({"status": "created"})

        add_subscriber_tool(imsi=self.valid_imsi)

        # Verify the structure of the subscriber object passed to add_subscriber
        args, _ = mock_add.call_args
        subscriber_obj = args[0]

        slice_cfg = subscriber_obj["slice"][0]
        self.assertEqual(slice_cfg["sst"], 1)
        self.assertTrue(slice_cfg["default_indicator"])
        self.assertEqual(slice_cfg["session"][0]["name"], "internet")
        self.assertEqual(slice_cfg["session"][0]["qos"]["index"], 9)

    @patch('src.tools.slices.Open5GSClient')
    def test_dedicated_slice_provisioning(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        # Existing subscriber with 1 slice
        mock_client.get_subscriber.return_value = json.dumps({
            "imsi": self.valid_imsi,
            "slice": [{"sst": 1, "default_indicator": True}]
        })
        mock_client.update_subscriber.return_value = json.dumps({"status": "updated"})

        new_slice = {"sst": 2, "default_indicator": False}
        add_slice(self.valid_imsi, new_slice)

        # Verify update_subscriber was called with both slices
        args, _ = mock_client.update_subscriber.call_args
        updated_sub = args[1]
        self.assertEqual(len(updated_sub["slice"]), 2)
        self.assertEqual(updated_sub["slice"][1]["sst"], 2)
        self.assertTrue(updated_sub["slice"][0]["default_indicator"])

    @patch('src.tools.slices.Open5GSClient')
    def test_duplicate_sst_failure(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_client.get_subscriber.return_value = json.dumps({
            "imsi": self.valid_imsi,
            "slice": [{"sst": 1, "default_indicator": True}]
        })

        # Attempt to add SST 1 again
        with self.assertRaises(ValueError) as cm:
            add_slice(self.valid_imsi, {"sst": 1})

        self.assertIn("already exists", str(cm.exception))
        mock_client.update_subscriber.assert_not_called()

    @patch('src.tools.subscribers.Open5GSClient')
    def test_backend_http_error(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        # Simulate a 500 Internal Server Error
        mock_client.get_subscriber.side_effect = requests.exceptions.HTTPError("500 Server Error")

        with self.assertRaises(requests.exceptions.HTTPError):
             from src.tools.subscribers import get_subscriber
             get_subscriber(self.valid_imsi)

    @patch('src.tools.slices.Open5GSClient')
    def test_partial_failure_provisioning(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        # Success on Read
        mock_client.get_subscriber.return_value = json.dumps({
            "imsi": self.valid_imsi,
            "slice": []
        })
        # Failure on Write
        mock_client.update_subscriber.side_effect = RuntimeError("Connection lost during write")

        with self.assertRaises(RuntimeError):
            add_slice(self.valid_imsi, {"sst": 2})
