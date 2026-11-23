from src.open5gs.rest_client import Open5GSClient
from src.open5gs.mongo_client import MongoDBClient
from src.tools.analytics import (
    get_core_status,
    get_network_summary
)

import json


def subscriber_exists(imsi):

    mongo = MongoDBClient()

    return {
        "exists":
            mongo.subscriber_exists(
                imsi
            )
    }

def get_subscriber_health(imsi):
    client = Open5GSClient()
    client.login()

    subscriber_text = client.get_subscriber(imsi)

    try:
        subscriber = json.loads(subscriber_text)
    except Exception:
        return {
            "exists": False
        }

    slices = subscriber.get(
        "slice",
        []
    )

    default_slice = None

    for s in slices:

        if s.get(
            "default_indicator",
            False
        ):
            default_slice = s["sst"]
            break

    qos_configured = False

    if slices:

        session = (
            slices[0]
            .get("session", [])
        )

        if (
            len(session) > 0
            and "ambr" in session[0]
        ):
            qos_configured = True

    return {
        "imsi": imsi,
        "exists": True,
        "slice_count": len(slices),
        "default_slice": default_slice,
        "qos_configured": qos_configured
    }


def get_network_health():

    core = get_core_status()

    summary = get_network_summary()

    healthy = (
        core["amf"] == "up"
        and core["smf"] == "up"
        and core["upf"] == "up"
        and core["nrf"] == "up"
        and core["udm"] == "up"
    )

    return {
        "status":
            "healthy"
            if healthy
            else "degraded",

        "amf": core["amf"],
        "smf": core["smf"],
        "upf": core["upf"],
        "nrf": core["nrf"],
        "udm": core["udm"],

        "active_ues":
            summary["active_ues"],

        "pfcp_sessions":
            summary["pfcp_sessions"],

        "pfcp_peers":
            summary["pfcp_peers"]
    }


def get_subscriber_report(imsi):

    client = Open5GSClient()
    client.login()

    # ---------------------------------------------------------
    # 1. Subscriber information
    # ---------------------------------------------------------

    subscriber_text = client.get_subscriber(imsi)
    subscriber = json.loads(subscriber_text)

    slices = subscriber.get("slice", [])

    # ---------------------------------------------------------
    # 2. Find default slice
    # ---------------------------------------------------------

    default_slice = None

    for slice_item in slices:

        if slice_item.get(
            "default_indicator",
            False
        ):
            default_slice = slice_item
            break

    # ---------------------------------------------------------
    # 3. Subscriber-level AMBR
    # ---------------------------------------------------------

    subscriber_ambr = subscriber.get(
        "ambr",
        {}
    )

    # ---------------------------------------------------------
    # 4. UE registration / PDU session
    # ---------------------------------------------------------

    from src.tools.network_ops import get_ue_status

    ue_status = get_ue_status(imsi)

    # ---------------------------------------------------------
    # 5. Health
    # ---------------------------------------------------------

    subscriber_health = get_subscriber_health(imsi)

    # ---------------------------------------------------------
    # 6. Build detailed report
    # ---------------------------------------------------------

    report = {
        "imsi": subscriber.get(
            "imsi",
            imsi
        ),

        "subscriber": subscriber,

        "ue_status": ue_status,

        "health": subscriber_health,

        "default_slice": (
            default_slice
            if default_slice is not None
            else None
        ),

        "subscriber_ambr": subscriber_ambr,

        "slices": slices
    }

    return report
