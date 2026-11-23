import re

from src.open5gs.mongo_client import MongoDBClient


class SessionParser:
    """Reconstruct session state from SMF log events."""

    def __init__(self):
        self.log_file = (
            "/home/student/"
            "Saquib/"
            "MCP-Server-for-Open5GS/"
            "docker_open5gs/"
            "log/"
            "smf.log"
        )
        self.mongo = MongoDBClient()

    def _get_configured_slice(self, imsi, dnn):
        subscriber = self.mongo.get_subscriber(imsi)

        if not subscriber:
            return {}

        slices = subscriber.get("slice", [])

        for slice_item in slices:
            for session in slice_item.get("session", []):
                if session.get("name") == dnn:
                    result = {}
                    if slice_item.get("sst") is not None:
                        result["sst"] = slice_item["sst"]
                    if slice_item.get("sd") is not None:
                        result["sd"] = slice_item["sd"]
                    return result

        for slice_item in slices:
            if slice_item.get("default_indicator", False):
                result = {}
                if slice_item.get("sst") is not None:
                    result["sst"] = slice_item["sst"]
                if slice_item.get("sd") is not None:
                    result["sd"] = slice_item["sd"]
                return result

        return {}

    def get_active_sessions(self):
        try:
            with open(
                self.log_file,
                "r",
                encoding="utf-8",
                errors="ignore",
            ) as file:
                lines = file.readlines()
        except OSError:
            return []

        # This deployment currently reports one session per IMSI/DNN.
        # A later creation event replaces the previous IP for that key.
        active_sessions = {}

        creation_pattern = re.compile(
            r"UE SUPI\[imsi-(.*?)\]"
            r"\s+DNN\[(.*?)\]"
            r"\s+IPv4\[(.*?)\]"
        )

        removal_pattern = re.compile(
            r"Removed Session:"
            r"\s+UE IMSI:\[imsi-(.*?)\]"
            r"\s+DNN:\[(.*?):\d+\]"
            r"\s+IPv4:\[(.*?)\]"
        )

        for line in lines:
            match = creation_pattern.search(line)

            if match:
                imsi, dnn, ipv4 = match.groups()

                if not self.mongo.subscriber_exists(imsi):
                    continue

                session_key = (imsi, dnn)
                configured_slice = self._get_configured_slice(imsi, dnn)

                session = {
                    "imsi": imsi,
                    "dnn": dnn,
                    "ipv4": ipv4,
                    "slice_source": "subscriber_configuration",
                }

                session.update(configured_slice)
                active_sessions[session_key] = session
                continue

            match = removal_pattern.search(line)

            if match:
                imsi, dnn, ipv4 = match.groups()
                session_key = (imsi, dnn)
                current = active_sessions.get(session_key)

                # Do not remove a newer session because of an older
                # removal event with a different IP address.
                if current and current.get("ipv4") == ipv4:
                    active_sessions.pop(session_key, None)

        return list(active_sessions.values())
