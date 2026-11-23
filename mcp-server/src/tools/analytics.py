from src.open5gs.rest_client import Open5GSClient
from src.open5gs.mongo_client import MongoDBClient

from src.tools.sessions import (
    get_session_metrics
)

import json
import subprocess


def get_core_status():

    containers = [
        "amf",
        "smf",
        "upf",
        "nrf",
        "udm"
    ]

    status = {}

    for container in containers:

        result = subprocess.run(
            [
                "docker",
                "inspect",
                "-f",
                "{{.State.Running}}",
                container
            ],
            capture_output=True,
            text=True
        )

        status[container] = (
            "up"
            if result.stdout.strip() == "true"
            else "down"
        )

    return status


def get_network_summary():

    mongo = MongoDBClient()

    metrics = get_session_metrics()

    return {
        "subscribers":
            mongo.count_subscribers(),

        "active_ues":
            metrics["ues_active"],

        "pfcp_sessions":
            metrics["pfcp_sessions_active"],

        "pfcp_peers":
            metrics["pfcp_peers_active"],

        "slices":
            mongo.count_total_slices()
    }


def get_subscriber_summary(imsi):

    client = Open5GSClient()
    client.login()

    subscriber_text = client.get_subscriber(
        imsi
    )

    subscriber = json.loads(
        subscriber_text
    )

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

    qos = (
        slices[0]
        ["session"][0]
        .get(
            "ambr",
            {}
        )
    )

    return {
        "imsi": imsi,

        "slice_count":
            len(slices),

        "default_slice":
            default_slice,

        "qos_dl":
            qos.get(
                "downlink",
                {}
            ).get(
                "value",
                0
            ),

        "qos_ul":
            qos.get(
                "uplink",
                {}
            ).get(
                "value",
                0
            )
    }
