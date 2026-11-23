import unittest

from src.tools.ue_registration import UEProfileError, build_ueransim_config


class BuildUERANSIMConfigTests(unittest.TestCase):
    def setUp(self):
        self.imsi = "001010000009990"
        self.profile = {
            "imsi": self.imsi,
            "security": {
                "k": "00112233445566778899AABBCCDDEEFF",
                "opc": "FFEEDDCCBBAA99887766554433221100",
                "amf": "8000",
            },
            "slice": [{
                "sst": 1,
                "sd": "000002",
                "default_indicator": True,
                "session": [{"name": "internet", "type": 3}],
            }],
        }

    def build(self, **overrides):
        args = {
            "imsi": self.imsi,
            "profile": self.profile,
            "gnb_ip": "172.22.0.23",
            "mcc": "001",
            "mnc": "01",
        }
        args.update(overrides)
        return build_ueransim_config(**args)

    def test_builds_config_from_profile(self):
        config = self.build()
        self.assertIn('supi: "imsi-001010000009990"', config)
        self.assertIn('mcc: "001"', config)
        self.assertIn('mnc: "01"', config)
        self.assertIn('apn: "internet"', config)
        self.assertIn('sd: "000002"', config)
        self.assertIn('opType: "OPC"', config)

    def test_includes_required_uac_configuration(self):
        config = self.build()
        self.assertIn("uacAic:", config)
        self.assertIn("mps: false", config)
        self.assertIn("mcs: false", config)
        self.assertIn("uacAcc:", config)
        self.assertIn("normalClass: 0", config)
        for class_number in range(11, 16):
            self.assertIn(f"class{class_number}: false", config)

    def test_session_type_override_selects_ipv4(self):
        config = self.build(session_type_override=1)
        self.assertIn('type: "IPv4"', config)
        self.assertNotIn('type: "IPv4v6"', config)

    def test_default_session_type_preserves_profile_mapping(self):
        config = self.build()
        self.assertIn('type: "IPv4v6"', config)

    def test_rejects_invalid_imsi(self):
        with self.assertRaises(UEProfileError):
            self.build(imsi="invalid")

    def test_rejects_profile_imsi_mismatch(self):
        with self.assertRaises(UEProfileError):
            self.build(imsi="001010000000123")

    def test_rejects_missing_security(self):
        profile = {"imsi": self.imsi, "slice": self.profile["slice"]}
        with self.assertRaises(UEProfileError):
            self.build(profile=profile)

    def test_rejects_malformed_key(self):
        profile = {
            **self.profile,
            "security": {**self.profile["security"], "k": "invalid"},
        }
        with self.assertRaises(UEProfileError):
            self.build(profile=profile)

    def test_rejects_missing_opc(self):
        security = dict(self.profile["security"])
        security.pop("opc")
        with self.assertRaises(UEProfileError):
            self.build(profile={**self.profile, "security": security})

    def test_rejects_invalid_gnb_ip(self):
        with self.assertRaises(UEProfileError):
            self.build(gnb_ip="not-an-ip")

    def test_rejects_profile_without_slices(self):
        with self.assertRaises(UEProfileError):
            self.build(profile={**self.profile, "slice": []})

    def test_supports_slice_without_sd(self):
        slice_item = dict(self.profile["slice"][0])
        slice_item.pop("sd")
        config = self.build(profile={**self.profile, "slice": [slice_item]})
        self.assertNotIn("sd:", config)


if __name__ == "__main__":
    unittest.main()


class FetchSubscriberProfileTests(unittest.TestCase):
    def setUp(self):
        self.imsi = "001010000009990"
        self.profile = {
            "imsi": self.imsi,
            "security": {
                "k": "00112233445566778899AABBCCDDEEFF",
                "opc": "FFEEDDCCBBAA99887766554433221100",
                "amf": "8000",
            },
            "slice": [{
                "sst": 1,
                "default_indicator": True,
                "session": [{"name": "internet", "type": 3}],
            }],
        }

    def test_fetches_profile_using_client(self):
        from unittest.mock import patch
        import json
        from src.tools.ue_registration import fetch_subscriber_profile

        with patch("src.open5gs.rest_client.Open5GSClient") as mock_client:
            instance = mock_client.return_value
            instance.get_subscriber.return_value = json.dumps(self.profile)

            result = fetch_subscriber_profile(self.imsi)

            instance.login.assert_called_once_with()
            instance.get_subscriber.assert_called_once_with(self.imsi)
            self.assertEqual(result["imsi"], self.imsi)
            self.assertEqual(result["security"]["amf"], "8000")

    def test_rejects_profile_for_different_imsi(self):
        from unittest.mock import patch
        import json
        from src.tools.ue_registration import (
            UEProfileError,
            fetch_subscriber_profile,
        )

        wrong_profile = {**self.profile, "imsi": "001010000000123"}
        with patch("src.open5gs.rest_client.Open5GSClient") as mock_client:
            mock_client.return_value.get_subscriber.return_value = json.dumps(wrong_profile)
            with self.assertRaises(UEProfileError):
                fetch_subscriber_profile(self.imsi)

    def test_sanitizes_client_errors(self):
        from unittest.mock import patch
        from src.tools.ue_registration import (
            UEProfileError,
            fetch_subscriber_profile,
        )

        with patch("src.open5gs.rest_client.Open5GSClient") as mock_client:
            mock_client.return_value.login.side_effect = RuntimeError(
                "sensitive test detail"
            )
            with self.assertRaises(UEProfileError) as caught:
                fetch_subscriber_profile(self.imsi)

        self.assertNotIn("sensitive test detail", str(caught.exception))

    def test_rejects_invalid_imsi_before_api_call(self):
        from unittest.mock import patch
        from src.tools.ue_registration import (
            UEProfileError,
            fetch_subscriber_profile,
        )

        with patch("src.open5gs.rest_client.Open5GSClient") as mock_client:
            with self.assertRaises(UEProfileError):
                fetch_subscriber_profile("invalid")
            mock_client.assert_not_called()
