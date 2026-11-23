"""Safely manage dedicated UERANSIM UE containers."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

MANAGED_LABEL = "org.open5gs-mcp.managed-ue"
NETWORK_NAME = "docker_open5gs_default"
IMAGE_NAME = "docker_ueransim"
CONTAINER_PREFIX = "mcp-ue-"
CONFIG_ROOT = (
    Path(tempfile.gettempdir())
    / f"open5gs-mcp-managed-ue-{os.getuid()}"
)
IMSI_PATTERN = re.compile(r"^\d{5,15}$")


class UEContainerError(RuntimeError):
    """A sanitized error from managed UE container operations."""


def _validate_imsi(imsi: str) -> None:
    if not isinstance(imsi, str) or not IMSI_PATTERN.fullmatch(imsi):
        raise UEContainerError("IMSI must contain 5 to 15 digits.")


def _container_name(imsi: str) -> str:
    _validate_imsi(imsi)
    return f"{CONTAINER_PREFIX}{imsi}"


def _config_dir(imsi: str) -> Path:
    return CONFIG_ROOT / _container_name(imsi)


def _run_docker(
    args: list[str], timeout: int = 30
) -> subprocess.CompletedProcess:
    """Run Docker without a shell and hide raw command output on errors."""
    try:
        return subprocess.run(
            ["docker", *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        raise UEContainerError("Docker operation failed.") from None


def _startup_diagnostic(name: str) -> str:
    """Capture bounded, sanitized startup diagnostics before rollback."""
    parts = []

    try:
        result = _run_docker([
            "inspect", "--format",
            "status={{.State.Status}} exit={{.State.ExitCode}}",
            name,
        ])
        details = result.stdout.strip()
        if details:
            parts.append(details[:150])
    except Exception:
        parts.append("Container state unavailable.")

    try:
        result = _run_docker(["logs", "--tail", "60", name])
        output = (result.stdout or "") + "\n" + (result.stderr or "")
        sensitive = re.compile(
            r"(?i)\b(key|opc|amf|password|token)\s*[:=]\s*[^\s,;]+"
        )
        lines = []
        for line in output.splitlines():
            line = "".join(ch for ch in line if ch.isprintable())
            line = sensitive.sub(r"\1=[REDACTED]", line)
            if re.search(
                r"(?i)error|failed|invalid|config|cannot|unable|exception",
                line,
            ):
                lines.append(line[:240])

        if lines:
            parts.append("log_excerpt=" + " | ".join(lines[-8:]))
        else:
            parts.append("No matching error lines in container logs.")
    except Exception:
        parts.append("Container logs unavailable.")

    return " ".join(parts)[:1800]

def _rollback_if_owned(name: str, imsi: str) -> bool:
    """Remove a container only after verifying both ownership labels."""
    try:
        result = _run_docker([
            "inspect", "--format", "{{json .Config.Labels}}", name
        ])
        labels = json.loads(result.stdout)
    except Exception:
        return False

    if not isinstance(labels, dict):
        return False

    if (
        labels.get(MANAGED_LABEL) != "true"
        or labels.get("org.open5gs-mcp.imsi") != imsi
    ):
        return False

    try:
        _run_docker(["stop", "--time", "5", name])
        _run_docker(["rm", name])
        return True
    except Exception:
        return False


def create_managed_ue(imsi: str, config_text: str) -> dict[str, str]:
    """Create one dedicated UE container with a protected configuration."""
    _validate_imsi(imsi)

    if not isinstance(config_text, str) or not config_text.strip():
        raise UEContainerError("A non-empty UE configuration is required.")

    name = _container_name(imsi)
    directory = _config_dir(imsi)
    created_directory = False
    docker_attempted = False

    try:
        CONFIG_ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)

        if CONFIG_ROOT.is_symlink():
            raise UEContainerError(
                "Managed configuration directory is unsafe."
            )

        os.chmod(CONFIG_ROOT, 0o700)

        # Refuse to overwrite existing state.
        directory.mkdir(mode=0o700, exist_ok=False)
        created_directory = True
        os.chmod(directory, 0o700)

        config_path = directory / "config.yaml"
        fd = os.open(
            config_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )

        with os.fdopen(fd, "w", encoding="utf-8") as config_file:
            config_file.write(config_text)

        docker_attempted = True
        result = _run_docker([
            "run", "-d",
            "--name", name,
            "--label", f"{MANAGED_LABEL}=true",
            "--label", f"org.open5gs-mcp.imsi={imsi}",
            "--network", NETWORK_NAME,
            "--cap-add", "NET_ADMIN",
            "--device", "/dev/net/tun:/dev/net/tun",
            "--mount",
            (
                f"type=bind,src={config_path},"
                "dst=/UERANSIM/config/managed-ue.yaml,readonly"
            ),
            "--restart", "no",
            IMAGE_NAME,
            "/UERANSIM/build/nr-ue",
            "-c", "/UERANSIM/config/managed-ue.yaml",
        ])

        container_id = result.stdout.strip()
        if not container_id:
            raise UEContainerError(
                "Docker did not return a container identifier."
            )

        state_result = _run_docker([
            "inspect", "--format", "{{.State.Running}}", name
        ])

        if state_result.stdout.strip().lower() != "true":
            # Capture diagnostics before rollback removes the container.
            diagnostic = _startup_diagnostic(name)
            raise UEContainerError(
                "Managed UE container did not enter running state. "
                f"Diagnostic: {diagnostic}"
            )

        return {
            "success": "true",
            "imsi": imsi,
            "container_name": name,
            "container_id": container_id,
            "status": "started",
        }

    except UEContainerError:
        rollback_ok = (
            _rollback_if_owned(name, imsi) if docker_attempted else True
        )

        if created_directory and rollback_ok:
            shutil.rmtree(directory, ignore_errors=True)

        raise

    except Exception:
        rollback_ok = (
            _rollback_if_owned(name, imsi) if docker_attempted else True
        )

        if created_directory and rollback_ok:
            shutil.rmtree(directory, ignore_errors=True)

        raise UEContainerError(
            "Could not create the managed UE container. "
            "No credentials were returned."
        ) from None


def stop_managed_ue(imsi: str) -> dict[str, str]:
    """Stop only a container with both expected ownership labels."""
    name = _container_name(imsi)

    try:
        result = _run_docker([
            "inspect", "--format", "{{json .Config.Labels}}", name
        ])
        labels = json.loads(result.stdout)
    except Exception:
        raise UEContainerError(
            "Managed UE was not found or could not be inspected."
        ) from None

    if not isinstance(labels, dict):
        raise UEContainerError(
            "Container ownership could not be verified."
        )

    if (
        labels.get(MANAGED_LABEL) != "true"
        or labels.get("org.open5gs-mcp.imsi") != imsi
    ):
        raise UEContainerError(
            "Refusing to stop a container whose ownership labels do not match."
        )

    _run_docker(["stop", "--time", "5", name])
    _run_docker(["rm", name])
    shutil.rmtree(_config_dir(imsi), ignore_errors=True)

    return {
        "success": "true",
        "imsi": imsi,
        "container_name": name,
        "status": "removed",
    }
