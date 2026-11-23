import json
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.tools import ue_container_manager as manager
from src.tools.ue_container_manager import (
    UEContainerError,
    create_managed_ue,
    stop_managed_ue,
)


class ManagedUEContainerTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.tempdir.name) / "managed"
        self.root_patch = patch.object(
            manager, "CONFIG_ROOT", self.config_root
        )
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.addCleanup(self.tempdir.cleanup)

        self.imsi = "001010000009990"
        self.config = (
            'supi: "imsi-001010000009990"\n'
            'key: "DUMMY_TEST_KEY"\n'
        )

    @staticmethod
    def completed(stdout="", stderr="", returncode=0):
        return subprocess.CompletedProcess(
            args=[],
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
        )

    def owned_labels(self):
        return json.dumps({
            manager.MANAGED_LABEL: "true",
            "org.open5gs-mcp.imsi": self.imsi,
        })

    @patch("src.tools.ue_container_manager.subprocess.run")
    def test_create_uses_owned_container_and_read_only_config(self, run):
        run.side_effect = [
            self.completed(stdout="dummy-container-id\n"),
            self.completed(stdout="true\n"),
        ]

        result = create_managed_ue(self.imsi, self.config)

        self.assertEqual(result["container_id"], "dummy-container-id")
        self.assertEqual(result["status"], "started")

        args = run.call_args_list[0].args[0]
        self.assertEqual(args[0:2], ["docker", "run"])
        self.assertIn("--network", args)
        self.assertIn(manager.NETWORK_NAME, args)
        self.assertIn(f"{manager.MANAGED_LABEL}=true", args)
        self.assertIn(f"org.open5gs-mcp.imsi={self.imsi}", args)
        self.assertIn("--cap-add", args)
        self.assertNotIn("--privileged", args)

        mount_arg = args[args.index("--mount") + 1]
        self.assertIn("readonly", mount_arg)
        self.assertIn(
            "dst=/UERANSIM/config/managed-ue.yaml", mount_arg
        )

        self.assertEqual(
            run.call_args_list[1].args[0][2:4],
            ["--format", "{{.State.Running}}"],
        )

        config_path = (
            self.config_root / f"mcp-ue-{self.imsi}" / "config.yaml"
        )
        self.assertEqual(config_path.read_text(), self.config)
        self.assertEqual(stat.S_IMODE(config_path.stat().st_mode), 0o600)
        self.assertEqual(
            stat.S_IMODE(config_path.parent.stat().st_mode), 0o700
        )

    @patch("src.tools.ue_container_manager.subprocess.run")
    def test_stopped_container_diagnostic_is_captured_before_rollback(
        self, run
    ):
        run.side_effect = [
            self.completed(stdout="container-id\n"),
            self.completed(stdout="false\n"),
            self.completed(stdout="status=exited exit=1\n"),
            self.completed(stdout="ERROR: invalid UE config\n"),
            self.completed(stdout=self.owned_labels()),
            self.completed(stdout="name\n"),
            self.completed(stdout="name\n"),
        ]

        with self.assertRaises(UEContainerError) as caught:
            create_managed_ue(self.imsi, self.config)

        message = str(caught.exception)
        self.assertIn("did not enter running state", message)
        self.assertIn("status=exited", message)

        self.assertIn("invalid UE config", message)
        self.assertEqual(run.call_count, 7)
        diagnostic_command = run.call_args_list[2].args[0]
        self.assertIn("inspect", diagnostic_command)
        self.assertTrue(
            any("{{.State.Status}}" in arg for arg in diagnostic_command)
        )
        self.assertIn(
            "{{json .Config.Labels}}",
            run.call_args_list[4].args[0],
        )
        self.assertEqual(run.call_args_list[5].args[0][1], "stop")
        self.assertEqual(run.call_args_list[6].args[0][1], "rm")

        self.assertFalse(
            (self.config_root / f"mcp-ue-{self.imsi}").exists()
        )

    @patch("src.tools.ue_container_manager.subprocess.run")
    def test_invalid_imsi_never_calls_docker(self, run):
        with self.assertRaises(UEContainerError):
            create_managed_ue("bad-imsi", self.config)
        run.assert_not_called()

    @patch("src.tools.ue_container_manager.subprocess.run")
    def test_empty_config_never_calls_docker(self, run):
        with self.assertRaises(UEContainerError):
            create_managed_ue(self.imsi, " ")
        run.assert_not_called()

    @patch("src.tools.ue_container_manager.subprocess.run")
    def test_refuses_to_overwrite_existing_config(self, run):
        directory = self.config_root / f"mcp-ue-{self.imsi}"
        directory.mkdir(parents=True)
        (directory / "config.yaml").write_text("existing")

        with self.assertRaises(UEContainerError):
            create_managed_ue(self.imsi, self.config)

        run.assert_not_called()
        self.assertEqual(
            (directory / "config.yaml").read_text(), "existing"
        )

    @patch("src.tools.ue_container_manager.subprocess.run")
    def test_sanitizes_docker_failure_and_preserves_config_if_unowned(
        self, run
    ):
        run.side_effect = [
            subprocess.CalledProcessError(
                1, ["docker"], stderr="sensitive test detail"
            ),
            subprocess.CalledProcessError(
                1, ["docker", "inspect"],
                stderr="sensitive inspect detail",
            ),
        ]

        with self.assertRaises(UEContainerError) as caught:
            create_managed_ue(self.imsi, self.config)

        self.assertNotIn("sensitive test detail", str(caught.exception))
        self.assertNotIn("sensitive inspect detail", str(caught.exception))

        directory = self.config_root / f"mcp-ue-{self.imsi}"
        self.assertTrue(directory.exists())
        self.assertEqual(
            (directory / "config.yaml").read_text(), self.config
        )
        self.assertEqual(run.call_count, 2)

    @patch("src.tools.ue_container_manager.subprocess.run")
    def test_empty_container_id_rolls_back_verified_owned_container(
        self, run
    ):
        run.side_effect = [
            self.completed(stdout=""),
            self.completed(stdout=self.owned_labels()),
            self.completed(stdout="name\n"),
            self.completed(stdout="name\n"),
        ]

        with self.assertRaises(UEContainerError):
            create_managed_ue(self.imsi, self.config)

        self.assertEqual(run.call_count, 4)
        self.assertIn(
            "{{json .Config.Labels}}",
            run.call_args_list[1].args[0],
        )
        self.assertEqual(run.call_args_list[2].args[0][1], "stop")
        self.assertEqual(run.call_args_list[3].args[0][1], "rm")
        self.assertFalse(
            (self.config_root / f"mcp-ue-{self.imsi}").exists()
        )

    @patch("src.tools.ue_container_manager.subprocess.run")
    def test_rollback_refuses_container_with_wrong_imsi_label(self, run):
        wrong_labels = json.dumps({
            manager.MANAGED_LABEL: "true",
            "org.open5gs-mcp.imsi": "001010000000001",
        })
        run.side_effect = [
            self.completed(stdout=""),
            self.completed(stdout=wrong_labels),
        ]

        with self.assertRaises(UEContainerError):
            create_managed_ue(self.imsi, self.config)

        self.assertEqual(run.call_count, 2)
        directory = self.config_root / f"mcp-ue-{self.imsi}"
        self.assertTrue(directory.exists())
        self.assertEqual(
            (directory / "config.yaml").read_text(), self.config
        )

    @patch("src.tools.ue_container_manager.subprocess.run")
    def test_stop_refuses_unowned_container(self, run):
        run.return_value = self.completed(
            stdout=json.dumps({
                manager.MANAGED_LABEL: "false",
                "org.open5gs-mcp.imsi": self.imsi,
            })
        )

        with self.assertRaises(UEContainerError):
            stop_managed_ue(self.imsi)

        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0][1], "inspect")

    @patch("src.tools.ue_container_manager.subprocess.run")
    def test_stop_removes_only_after_label_verification(self, run):
        run.side_effect = [
            self.completed(stdout=self.owned_labels()),
            self.completed(stdout="name\n"),
            self.completed(stdout="name\n"),
        ]

        directory = self.config_root / f"mcp-ue-{self.imsi}"
        directory.mkdir(parents=True)
        (directory / "config.yaml").write_text(self.config)

        result = stop_managed_ue(self.imsi)

        self.assertEqual(result["status"], "removed")
        self.assertEqual(run.call_count, 3)
        self.assertEqual(run.call_args_list[1].args[0][1], "stop")
        self.assertEqual(run.call_args_list[2].args[0][1], "rm")
        self.assertFalse(directory.exists())


if __name__ == "__main__":
    unittest.main()
