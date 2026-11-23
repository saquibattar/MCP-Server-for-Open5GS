"""Offline validation and UERANSIM config generation.

No API calls, container operations, filesystem writes, or credential logging
are performed by this module.
"""
import ipaddress
import json
import re
from typing import Any


class UEProfileError(ValueError):
    """Raised when a subscriber profile cannot configure a UE safely."""


_IMSI_RE = re.compile(r"^\d{5,15}$")
_HEX32_RE = re.compile(r"^[0-9a-fA-F]{32}$")
_HEX4_RE = re.compile(r"^[0-9a-fA-F]{4}$")
_HEX6_RE = re.compile(r"^[0-9a-fA-F]{6}$")


def _yaml_string(value: str) -> str:
    # JSON-quoted strings are also valid YAML scalar strings.
    return json.dumps(value, ensure_ascii=True)


def _select_session(profile: dict[str, Any]):
    slices = profile.get("slice")
    if not isinstance(slices, list) or not slices:
        raise UEProfileError("Subscriber profile has no configured slices.")

    candidates = []
    for slice_item in slices:
        if not isinstance(slice_item, dict):
            continue
        sessions = slice_item.get("session")
        if not isinstance(sessions, list):
            continue
        for session in sessions:
            if (
                isinstance(session, dict)
                and isinstance(session.get("name"), str)
                and session["name"].strip()
            ):
                candidates.append((slice_item, session))

    if not candidates:
        raise UEProfileError("Subscriber profile has no usable DNN session.")

    for slice_item, session in candidates:
        if slice_item.get("default_indicator") is True:
            return slice_item, session

    return candidates[0]


def build_ueransim_config(
    imsi: str,
    profile: dict[str, Any],
    gnb_ip: str,
    mcc: str,
    mnc: str,
    session_type_override: int | None = None,
) -> str:
    """Validate a profile and build a UERANSIM UE YAML config in memory."""
    if not isinstance(imsi, str) or not _IMSI_RE.fullmatch(imsi):
        raise UEProfileError("IMSI must contain 5 to 15 digits.")

    if not isinstance(profile, dict):
        raise UEProfileError("Subscriber profile must be an object.")

    profile_imsi = profile.get("imsi")
    if profile_imsi is not None and str(profile_imsi) != imsi:
        raise UEProfileError("Subscriber profile IMSI does not match the request.")

    if not isinstance(mcc, str) or not re.fullmatch(r"\d{3}", mcc):
        raise UEProfileError("MCC must contain exactly 3 digits.")
    if not isinstance(mnc, str) or not re.fullmatch(r"\d{2,3}", mnc):
        raise UEProfileError("MNC must contain 2 or 3 digits.")

    try:
        address = ipaddress.ip_address(gnb_ip)
    except (ValueError, TypeError):
        raise UEProfileError("gNB address must be a valid IP address.") from None
    if address.version != 4:
        raise UEProfileError("The current configuration requires an IPv4 gNB address.")

    security = profile.get("security")
    if not isinstance(security, dict):
        raise UEProfileError("Subscriber profile has no security configuration.")

    key = security.get("k")
    opc = security.get("opc")
    amf = security.get("amf")

    if not isinstance(key, str) or not _HEX32_RE.fullmatch(key):
        raise UEProfileError("Subscriber profile has no valid 128-bit K value.")
    if not isinstance(opc, str) or not _HEX32_RE.fullmatch(opc):
        raise UEProfileError("Subscriber profile has no valid 128-bit OPc value.")
    if not isinstance(amf, str) or not _HEX4_RE.fullmatch(amf):
        raise UEProfileError("Subscriber profile has no valid 16-bit AMF value.")

    slice_item, session = _select_session(profile)

    sst = slice_item.get("sst")
    if isinstance(sst, bool) or not isinstance(sst, int) or not 1 <= sst <= 255:
        raise UEProfileError("Subscriber profile has an invalid SST.")

    sd = slice_item.get("sd")
    if sd is not None:
        sd = str(sd)
        if not _HEX6_RE.fullmatch(sd):
            raise UEProfileError("Subscriber profile has an invalid slice SD.")

    dnn = session["name"].strip()
    session_type = session.get("type", 3)
    if isinstance(session_type, str) and session_type.isdigit():
        session_type = int(session_type)

    if session_type_override is not None:
        session_type = session_type_override

    type_map = {
        1: "IPv4",
        2: "IPv6",
        3: "IPv4v6",
        4: "Ethernet",
        5: "Unstructured",
    }
    if session_type not in type_map:
        raise UEProfileError("Subscriber profile has an unsupported PDU session type.")

    lines = [
        f"supi: {_yaml_string('imsi-' + imsi)}",
        f"mcc: {_yaml_string(mcc)}",
        f"mnc: {_yaml_string(mnc)}",
        f"key: {_yaml_string(key)}",
        f"op: {_yaml_string(opc)}",
        'opType: "OPC"',
        f"amf: {_yaml_string(amf)}",
        "gnbSearchList:",
        f"  - {_yaml_string(str(address))}",
        "uacAic:",
        "  mps: false",
        "  mcs: false",
        "uacAcc:",
        "  normalClass: 0",
        "  class11: false",
        "  class12: false",
        "  class13: false",
        "  class14: false",
        "  class15: false",
        "sessions:",
        f"  - type: {_yaml_string(type_map[session_type])}",
        f"    apn: {_yaml_string(dnn)}",
        "    slice:",
        f"      sst: {sst}",
    ]

    if sd is not None:
        lines.append(f"      sd: {_yaml_string(sd)}")

    lines.extend([
        "configured-nssai:",
        f"  - sst: {sst}",
        "default-nssai:",
        f"  - sst: {sst}",
        "integrity:",
        "  IA1: true",
        "  IA2: true",
        "  IA3: true",
        "ciphering:",
        "  EA1: true",
        "  EA2: true",
        "  EA3: true",
        "integrityMaxRate:",
        '  uplink: "full"',
        '  downlink: "full"',
        "",
    ])

    return "\n".join(lines)


def fetch_subscriber_profile(imsi: str) -> dict[str, Any]:
    """Fetch a subscriber profile internally, without exposing secrets.

    This function must be called from a process whose environment already
    contains OPEN5GS_USERNAME and OPEN5GS_PASSWORD.
    """
    if not isinstance(imsi, str) or not _IMSI_RE.fullmatch(imsi):
        raise UEProfileError("IMSI must contain 5 to 15 digits.")

    # Import lazily so offline configuration tests do not require API access.
    from src.open5gs.rest_client import Open5GSClient

    try:
        client = Open5GSClient()
        client.login()
        raw_profile = client.get_subscriber(imsi)
        import json as _json
        profile = _json.loads(raw_profile)
    except Exception:
        # Do not propagate exception details that could contain sensitive data.
        raise UEProfileError(
            "Unable to retrieve the subscriber profile from Open5GS."
        ) from None

    if not isinstance(profile, dict):
        raise UEProfileError("Open5GS returned an invalid subscriber profile.")

    if str(profile.get("imsi", "")) != imsi:
        raise UEProfileError(
            "Open5GS returned a profile that does not match the requested IMSI."
        )

    security = profile.get("security")
    if not isinstance(security, dict):
        raise UEProfileError("Subscriber profile has no security configuration.")

    if not all(
        isinstance(security.get(field), str)
        for field in ("k", "opc", "amf")
    ):
        raise UEProfileError(
            "Subscriber profile is missing required authentication fields."
        )

    # Return the profile only to trusted internal code. Never log or expose it
    # through an MCP tool response.
    return profile
