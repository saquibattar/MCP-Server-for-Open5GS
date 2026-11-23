def subscriber_links(imsi):

    return {

        "self": {
            "tool": "get_subscriber_tool",
            "parameters": {
                "imsi": imsi
            },
            "description": "Retrieve this subscriber."
        },

        "summary": {
            "tool": "get_subscriber_summary_tool",
            "parameters": {
                "imsi": imsi
            },
            "description": "Get a summary of this subscriber."
        },

        "health": {
            "tool": "get_subscriber_health_tool",
            "parameters": {
                "imsi": imsi
            },
            "description": "Check subscriber health."
        },

        "report": {
            "tool": "get_subscriber_report_tool",
            "parameters": {
                "imsi": imsi
            },
            "description": "Generate a detailed subscriber report."
        },

        "qos": {
            "tool": "get_qos_tool",
            "parameters": {
                "imsi": imsi
            },
            "description": "Retrieve subscriber QoS configuration."
        },

        "slices": {
            "tool": "list_slices_tool",
            "parameters": {
                "imsi": imsi
            },
            "description": "List all slices assigned to this subscriber."
        },

        "ue_status": {
            "tool": "get_ue_status_tool",
            "parameters": {
                "imsi": imsi
            },
            "description": "Retrieve UE registration and PDU session status."
        },

        "update": {
            "tool": "update_subscriber_tool",
            "parameters": {
                "imsi": imsi
            },
            "requires": [
                "subscriber"
            ],
            "description": "Update this subscriber."
        },

        "delete": {
            "tool": "delete_subscriber_tool",
            "parameters": {
                "imsi": imsi
            },
            "description": "Delete this subscriber."
        }
    }


def slice_links(imsi, sst):

    return {

        "subscriber": {
            "tool": "get_subscriber_tool",
            "parameters": {
                "imsi": imsi
            },
            "description": "Retrieve the owning subscriber."
        },

        "slice_qos": {
            "tool": "get_slice_qos_tool",
            "parameters": {
                "imsi": imsi,
                "sst": sst
            },
            "description": "Retrieve QoS configuration for this slice."
        },

        "update_qos": {
            "tool": "update_slice_qos_tool",
            "parameters": {
                "imsi": imsi,
                "sst": sst
            },
            "requires": [
                "downlink",
                "uplink"
            ],
            "description": "Update QoS configuration for this slice."
        },

        "update": {
            "tool": "update_slice_tool",
            "parameters": {
                "imsi": imsi,
                "sst": sst
            },
            "requires": [
                "default_indicator"
            ],
            "description": "Update this slice."
        },

        "delete": {
            "tool": "delete_slice_tool",
            "parameters": {
                "imsi": imsi,
                "sst": sst
            },
            "description": "Delete this slice."
        }
    }


def qos_links(imsi):

    return {

        "subscriber": {
            "tool": "get_subscriber_tool",
            "parameters": {
                "imsi": imsi
            },
            "description": "Retrieve this subscriber."
        },

        "subscriber_health": {
            "tool": "get_subscriber_health_tool",
            "parameters": {
                "imsi": imsi
            },
            "description": "Check subscriber health."
        },

        "update_qos": {
            "tool": "update_qos_tool",
            "parameters": {
                "imsi": imsi
            },
            "requires": [
                "downlink",
                "uplink"
            ],
            "description": "Update subscriber QoS."
        },

        "slice_qos": {
            "tool": "get_slice_qos_tool",
            "parameters": {
                "imsi": imsi
            },
            "requires": [
                "sst"
            ],
            "description": "Retrieve QoS for a specific slice."
        }
    }


def network_links():

    return {

        "network_summary": {
            "tool": "get_network_summary_tool",
            "description": "Retrieve network summary."
        },

        "core_status": {
            "tool": "get_core_status_tool",
            "description": "Retrieve Open5GS core status."
        },

        "network_health": {
            "tool": "get_network_health_tool",
            "description": "Retrieve Open5GS health status."
        },

        "session_metrics": {
            "tool": "get_session_metrics_tool",
            "description": "Retrieve Open5GS session metrics."
        },

        "active_ues": {
            "tool": "get_active_ues_tool",
            "description": "Retrieve active UE count."
        },

        "pfcp_sessions": {
            "tool": "get_pfcp_sessions_tool",
            "description": "Retrieve active PFCP session count."
        },

        "pfcp_peers": {
            "tool": "get_pfcp_peers_tool",
            "description": "Retrieve active PFCP peer count."
        },

        "pdu_sessions": {
            "tool": "list_pdu_sessions_tool",
            "description": "List active PDU sessions."
        },

        "slice_usage": {
            "tool": "get_slice_usage_tool",
            "requires": [
                "sst"
            ],
            "description": "Retrieve subscriber usage statistics for a network slice."
        }
    }


def ue_links(imsi):

    return {

        "subscriber": {
            "tool": "get_subscriber_tool",
            "parameters": {
                "imsi": imsi
            },
            "description": "Retrieve this subscriber."
        },

        "health": {
            "tool": "get_subscriber_health_tool",
            "parameters": {
                "imsi": imsi
            },
            "description": "Retrieve subscriber health."
        },

        "report": {
            "tool": "get_subscriber_report_tool",
            "parameters": {
                "imsi": imsi
            },
            "description": "Generate subscriber report."
        },

        "qos": {
            "tool": "get_qos_tool",
            "parameters": {
                "imsi": imsi
            },
            "description": "Retrieve subscriber QoS."
        },

        "slices": {
            "tool": "list_slices_tool",
            "parameters": {
                "imsi": imsi
            },
            "description": "Retrieve subscriber slices."
        }
    }


def pdu_links(imsi):

    return {

        "subscriber": {
            "tool": "get_subscriber_tool",
            "parameters": {
                "imsi": imsi
            },
            "description": "Retrieve subscriber information."
        },

        "subscriber_health": {
            "tool": "get_subscriber_health_tool",
            "parameters": {
                "imsi": imsi
            },
            "description": "Retrieve subscriber health."
        },

        "ue_status": {
            "tool": "get_ue_status_tool",
            "parameters": {
                "imsi": imsi
            },
            "description": "Retrieve UE registration status."
        },

        "qos": {
            "tool": "get_qos_tool",
            "parameters": {
                "imsi": imsi
            },
            "description": "Retrieve subscriber QoS."
        },

        "slices": {
            "tool": "list_slices_tool",
            "parameters": {
                "imsi": imsi
            },
            "description": "Retrieve subscriber slices."
        }
    }
