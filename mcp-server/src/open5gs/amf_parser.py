import re


class AMFParser:

    def __init__(self):

        self.log_file = (
            "/home/student/"
            "Saquib/"
            "MCP-Server-for-Open5GS/"
            "docker_open5gs/"
            "log/"
            "amf.log"
        )

    def is_registered(self, imsi):

        try:

            with open(
                self.log_file,
                "r",
                encoding="utf-8",
                errors="ignore"
            ) as file:

                lines = file.readlines()

        except Exception:

            return False

        registered = False

        registration_pattern = re.compile(
            rf"\[imsi-{re.escape(imsi)}\]"
            r"\s+Registration complete"
        )

        for line in lines:

            if registration_pattern.search(line):

                registered = True
                continue

            if (
                registered
                and "UE Context Release" in line
            ):

                registered = False

        return registered
