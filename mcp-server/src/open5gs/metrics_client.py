import requests
import re


class MetricsClient:

    def __init__(self):

        self.metrics_url = (
            "http://172.22.0.7:9091/metrics"
        )

    def get_metrics(self):

        response = requests.get(
            self.metrics_url,
            timeout=5
        )

        response.raise_for_status()

        metrics = {}

        for line in response.text.splitlines():

            if not line or line.startswith("#"):
                continue

            parts = line.split()

            if len(parts) != 2:
                continue

            metric_expression = parts[0]
            metric_value = parts[1]

            try:

                value = float(
                    metric_value
                )

            except ValueError:

                continue

            match = re.match(
                r"^([^{]+)(?:\{(.*)\})?$",
                metric_expression
            )

            if not match:
                continue

            metric_name = match.group(1)
            labels_text = match.group(2)

            labels = {}

            if labels_text:

                for label_match in re.finditer(
                    r'(\w+)="([^"]*)"',
                    labels_text
                ):

                    labels[
                        label_match.group(1)
                    ] = label_match.group(2)

            if labels:

                metrics[
                    (
                        metric_name,
                        tuple(
                            sorted(
                                labels.items()
                            )
                        )
                    )
                ] = value

            else:

                metrics[
                    metric_name
                ] = value

        return metrics

    def get_metric(
        self,
        metric_name,
        labels=None
    ):

        labels = labels or {}

        metrics = self.get_metrics()

        # Exact match for metrics without labels
        if not labels:

            return metrics.get(
                metric_name,
                0
            )

        # Find a metric with matching requested labels.
        # Additional Prometheus labels are allowed.
        for key, value in metrics.items():

            if not isinstance(key, tuple):
                continue

            stored_metric_name = key[0]
            stored_labels = dict(key[1])

            if stored_metric_name != metric_name:
                continue

            if all(
                stored_labels.get(
                    label_name
                ) == str(label_value)
                for label_name, label_value
                in labels.items()
            ):

                return value

        return 0
