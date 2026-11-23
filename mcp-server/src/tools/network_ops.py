from src.open5gs.session_parser import SessionParser
from src.open5gs.metrics_client import MetricsClient
from src.open5gs.runtime_state import RuntimeState


# Verified from the running UPF container and its listening sockets.
# This is deployment-level endpoint information, not a per-session
# UPF attribution confirmed from live session state.
UPF_ENDPOINT = {
    "address": "172.22.0.8",
    "gtpu_port": 2152,
    "pfcp_port": 8805,
    "transport": "UDP",
    "source": "running_upf_container",
}


def _normalise_session(session):
    """Normalize session fields without inventing missing session data."""
    result = dict(session)

    if "ip_address" not in result:
        for key in ("ipv4", "ue_ip", "ip", "ipv4_address"):
            if result.get(key) is not None:
                result["ip_address"] = result[key]
                break

    snssai = result.get("snssai")

    if isinstance(snssai, dict):
        slice_identifier = dict(snssai)

        if "sst" not in slice_identifier and result.get("sst") is not None:
            slice_identifier["sst"] = result["sst"]

        if "sd" not in slice_identifier and result.get("sd") is not None:
            slice_identifier["sd"] = result["sd"]

        if slice_identifier:
            result["slice_identifier"] = slice_identifier

    elif result.get("sst") is not None:
        slice_identifier = {"sst": result["sst"]}

        if result.get("sd") is not None:
            slice_identifier["sd"] = result["sd"]

        result["slice_identifier"] = slice_identifier

    # Do not overwrite a UPF field supplied by a future session-aware parser.
    if "upf_anchor_point" not in result:
        result["upf_endpoint"] = dict(UPF_ENDPOINT)
        result["upf_attribution"] = (
            "deployment_endpoint_not_individually_correlated_to_session"
        )

    return result


def list_pdu_sessions(dnn=None):
    """List reconstructed PDU sessions, optionally filtered by DNN."""
    parser = SessionParser()
    runtime = RuntimeState()

    sessions = parser.get_active_sessions() or []

    if not runtime.is_ue_running():
        sessions = []

    normalized_sessions = [
        _normalise_session(session)
        for session in sessions
        if isinstance(session, dict)
    ]

    if dnn:
        normalized_sessions = [
            session
            for session in normalized_sessions
            if session.get("dnn") == dnn
        ]

    return {
        "active_sessions": len(normalized_sessions),
        "sessions": normalized_sessions,
        "upf_endpoint": dict(UPF_ENDPOINT),
        "session_source": "reconstructed_from_smf_logs",
    }


def get_ue_status(imsi):
    """Return UE status based on reconstructed SMF session data."""
    parser = SessionParser()
    sessions = parser.get_active_sessions() or []

    session = next(
        (
            item
            for item in sessions
            if isinstance(item, dict) and item.get("imsi") == imsi
        ),
        None,
    )

    runtime = RuntimeState()
    ue_running = runtime.is_ue_running()
    registered = ue_running and session is not None
    pdu_session_active = ue_running and session is not None

    result = {
        "imsi": imsi,
        "registered": registered,
        "pdu_session_active": pdu_session_active,
    }

    if session is not None:
        result["session"] = _normalise_session(session)

    return result


def get_slice_usage(sst):
    """Return configured subscriber count and active-session metrics."""
    from src.open5gs.mongo_client import MongoDBClient

    mongo = MongoDBClient()
    configured_subscribers = mongo.count_slice_usage(sst)

    metrics = MetricsClient()
    active_sessions = metrics.get_metric(
        "fivegs_smffunction_sm_sessionnbr",
        {"snssai": str(sst)},
    )

    return {
        "sst": sst,
        "configured_subscribers": configured_subscribers,
        "active_sessions": active_sessions,
    }
