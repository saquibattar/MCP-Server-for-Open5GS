from src.open5gs.rest_client import Open5GSClient
import json


def _get_subscriber(client, imsi):
    """Retrieve and decode an Open5GS subscriber record."""
    subscriber_text = client.get_subscriber(imsi)

    if isinstance(subscriber_text, str):
        subscriber = json.loads(subscriber_text)
    else:
        subscriber = subscriber_text

    if not isinstance(subscriber, dict):
        raise ValueError(
            f"Unexpected subscriber response for IMSI {imsi}."
        )

    return subscriber


def _get_session(subscriber, imsi, sst=None):
    """
    Find the first configured session, or the session belonging to
    the requested SST. Returns (slice_item, session) or (None, None).
    """
    slices = subscriber.get("slice", [])

    for slice_item in slices:
        if sst is not None and slice_item.get("sst") != sst:
            continue

        sessions = slice_item.get("session", [])
        if sessions:
            return slice_item, sessions[0]

    return None, None


def _qos_result(imsi, slice_item, session):
    """Build a consistent QoS response."""
    qos = session.get("qos", {})
    arp = qos.get("arp")

    return {
        "imsi": imsi,
        "sst": slice_item.get("sst"),
        "dnn": session.get("name"),
        "ambr": session.get("ambr", {}),
        "five_qi": qos.get("index"),
        "arp": arp
    }


def get_qos(imsi):
    """Retrieve AMBR, 5QI and ARP for the first configured session."""
    client = Open5GSClient()
    client.login()

    subscriber = _get_subscriber(client, imsi)
    slice_item, session = _get_session(subscriber, imsi)

    if slice_item is None:
        return {
            "error": f"Subscriber {imsi} has no configured QoS session.",
            "imsi": imsi
        }

    return _qos_result(imsi, slice_item, session)


def update_qos(
    imsi,
    downlink,
    uplink,
    unit=2,
    five_qi=None,
    arp_priority_level=None,
    arp_pre_emption_capability=None,
    arp_pre_emption_vulnerability=None
):
    """
    Update subscriber-level session AMBR and optionally 5QI and ARP.

    ARP fields that are omitted are left unchanged.
    """
    if downlink < 0 or uplink < 0:
        return {
            "error": "AMBR values cannot be negative.",
            "imsi": imsi
        }

    if unit not in (0, 1, 2, 3, 4):
        return {
            "error": "Invalid AMBR unit. Use 0=bps, 1=Kbps, 2=Mbps, 3=Gbps, or 4=Tbps.",
            "imsi": imsi
        }

    if five_qi is not None and not 1 <= five_qi <= 255:
        return {
            "error": "5QI must be between 1 and 255.",
            "imsi": imsi
        }

    if (
        arp_priority_level is not None
        and not 1 <= arp_priority_level <= 15
    ):
        return {
            "error": "ARP priority level must be between 1 and 15.",
            "imsi": imsi
        }

    for field_name, value in (
        ("arp_pre_emption_capability", arp_pre_emption_capability),
        ("arp_pre_emption_vulnerability", arp_pre_emption_vulnerability)
    ):
        if value is not None and value not in (0, 1):
            return {
                "error": f"{field_name} must be 0 or 1.",
                "imsi": imsi
            }

    client = Open5GSClient()
    client.login()

    subscriber = _get_subscriber(client, imsi)
    slice_item, session = _get_session(subscriber, imsi)

    if slice_item is None:
        return {
            "error": f"Subscriber {imsi} has no configured QoS session.",
            "imsi": imsi
        }

    # Update session AMBR.
    session["ambr"] = {
        "downlink": {
            "value": downlink,
            "unit": unit
        },
        "uplink": {
            "value": uplink,
            "unit": unit
        }
    }

    qos = session.setdefault("qos", {})

    if five_qi is not None:
        qos["index"] = five_qi

    # Update only explicitly supplied ARP fields.
    arp_fields = {
        "priority_level": arp_priority_level,
        "pre_emption_capability": arp_pre_emption_capability,
        "pre_emption_vulnerability": arp_pre_emption_vulnerability
    }

    supplied_arp_fields = {
        key: value
        for key, value in arp_fields.items()
        if value is not None
    }

    if supplied_arp_fields:
        arp = qos.setdefault("arp", {})
        arp.update(supplied_arp_fields)

    response = client.update_subscriber(imsi, subscriber)

    if isinstance(response, str):
        result = json.loads(response)
    else:
        result = response

    # Return the update result and the requested values. The caller can
    # use get_qos() afterwards to verify the persisted Open5GS values.
    return {
        "imsi": imsi,
        "update_result": result,
        "requested_qos": _qos_result(imsi, slice_item, session)
    }


def get_slice_qos(imsi, sst):
    """Retrieve AMBR, 5QI and ARP for a specific SST."""
    client = Open5GSClient()
    client.login()

    subscriber = _get_subscriber(client, imsi)
    slice_item, session = _get_session(subscriber, imsi, sst=sst)

    if slice_item is None:
        return {
            "error": f"Slice SST {sst} not found or has no QoS session.",
            "imsi": imsi,
            "sst": sst
        }

    return _qos_result(imsi, slice_item, session)



def update_slice_qos(
    imsi,
    sst,
    downlink,
    uplink,
    unit=2,
    five_qi=None
):
    """Update session AMBR and optionally 5QI for a specific SST."""

    if downlink < 0 or uplink < 0:
        return {
            "error": "AMBR values cannot be negative.",
            "imsi": imsi,
            "sst": sst
        }

    if unit not in (0, 1, 2, 3, 4):
        return {
            "error": (
                "Invalid AMBR unit. Use 0=bps, 1=Kbps, "
                "2=Mbps, 3=Gbps, or 4=Tbps."
            ),
            "imsi": imsi,
            "sst": sst
        }

    if five_qi is not None:
        if (
            isinstance(five_qi, bool)
            or not isinstance(five_qi, int)
            or not 1 <= five_qi <= 255
        ):
            return {
                "error": "5QI must be an integer between 1 and 255.",
                "imsi": imsi,
                "sst": sst
            }

    client = Open5GSClient()
    client.login()

    subscriber = _get_subscriber(client, imsi)
    slice_item, session = _get_session(
        subscriber,
        imsi,
        sst=sst
    )

    if slice_item is None:
        return {
            "error": f"Slice SST {sst} not found or has no QoS session.",
            "imsi": imsi,
            "sst": sst
        }

    # Update AMBR and preserve unrelated session configuration.
    session["ambr"] = {
        "downlink": {
            "value": downlink,
            "unit": unit
        },
        "uplink": {
            "value": uplink,
            "unit": unit
        }
    }

    # Change 5QI only when the caller explicitly supplies it.
    if five_qi is not None:
        qos = session.setdefault("qos", {})
        qos["index"] = five_qi

    # Persist the subscriber document.
    response = client.update_subscriber(imsi, subscriber)

    if isinstance(response, str):
        result = json.loads(response)
    else:
        result = response

    updated_fields = {
        "ambr": True,
        "five_qi": five_qi is not None
    }

    # Verify a requested 5QI change against a fresh read.
    if five_qi is not None:
        updated_subscriber = _get_subscriber(client, imsi)
        updated_slice, updated_session = _get_session(
            updated_subscriber,
            imsi,
            sst=sst
        )

        actual_five_qi = None

        if updated_session is not None:
            actual_five_qi = (
                updated_session.get("qos", {}).get("index")
            )

        if actual_five_qi != five_qi:
            return {
                "success": False,
                "verification_passed": False,
                "error": (
                    "5QI update verification failed: persisted value "
                    "does not match the requested value."
                ),
                "imsi": imsi,
                "sst": sst,
                "requested_five_qi": five_qi,
                "actual_five_qi": actual_five_qi,
                "update_result": result
            }

    return {
        "success": True,
        "verification_passed": five_qi is not None,
        "imsi": imsi,
        "sst": sst,
        "update_result": result,
        "updated_fields": updated_fields,
        "requested_ambr": session["ambr"],
        "requested_five_qi": five_qi
    }
