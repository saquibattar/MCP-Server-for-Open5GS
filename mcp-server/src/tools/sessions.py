from src.open5gs.metrics_client import MetricsClient


def get_session_metrics():
    client = MetricsClient()

    metrics = client.get_metrics()

    return {
        "ues_active": metrics.get("ues_active", 0),
        "pfcp_peers_active": metrics.get("pfcp_peers_active", 0),
        "pfcp_sessions_active": metrics.get("pfcp_sessions_active", 0),
        "gtp2_sessions_active": metrics.get(
            "gtp2_sessions_active",
            0
        ),
        "bearers_active": metrics.get(
            "bearers_active",
            0
        )
    }


def get_active_ues():
    metrics = get_session_metrics()

    return {
        "active_ues": metrics["ues_active"]
    }


def get_pfcp_sessions():
    metrics = get_session_metrics()

    return {
        "pfcp_sessions": metrics["pfcp_sessions_active"]
    }


def get_pfcp_peers():
    metrics = get_session_metrics()

    return {
        "pfcp_peers": metrics["pfcp_peers_active"]
    }
