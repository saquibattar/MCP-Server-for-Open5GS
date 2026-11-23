import subprocess


class RuntimeState:

    def __init__(self):
        self.ue_container = "nr_ue"

    def is_ue_running(self):

        try:

            result = subprocess.run(
                [
                    "docker",
                    "inspect",
                    "-f",
                    "{{.State.Running}}",
                    self.ue_container
                ],
                capture_output=True,
                text=True,
                timeout=5
            )

            return result.stdout.strip() == "true"

        except Exception:

            return False
