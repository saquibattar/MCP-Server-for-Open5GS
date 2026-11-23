from src.open5gs.rest_client import Open5GSClient
import json


def list_slices(imsi):
    client = Open5GSClient()
    client.login()

    subscriber_text = client.get_subscriber(imsi)
    subscriber = json.loads(subscriber_text)

    slices = subscriber.get("slice", [])

    return {
        "slice_count": len(slices),
        "slices": slices
    }


def add_slice(imsi, slice_data):
    client = Open5GSClient()
    client.login()

    subscriber_text = client.get_subscriber(imsi)
    subscriber = json.loads(subscriber_text)

    if "slice" not in subscriber:
        subscriber["slice"] = []

    # Prevent duplicate SST values
    new_sst = slice_data.get("sst")

    for existing_slice in subscriber["slice"]:
        if existing_slice.get("sst") == new_sst:
            raise ValueError(
                f"Slice with SST {new_sst} already exists "
                f"for subscriber {imsi}."
            )

    # If no session was supplied, create a default session
    # so the slice is immediately usable for QoS configuration.
    if not slice_data.get("session"):
        slice_data["session"] = [
            {
                "name": "internet",
                "type": 3,
                "qos": {
                    "index": 9,
                    "arp": {
                        "priority_level": 8,
                        "pre_emption_capability": 1,
                        "pre_emption_vulnerability": 1
                    }
                },
                "ambr": {
                    "downlink": {
                        "value": 1,
                        "unit": 3
                    },
                    "uplink": {
                        "value": 1,
                        "unit": 3
                    }
                }
            }
        ]

    # If this is the first slice, make it the default.
    # Otherwise respect the requested default_indicator.
    if len(subscriber["slice"]) == 0:
        slice_data["default_indicator"] = True

    else:
        if slice_data.get("default_indicator") is True:
            # Only one slice can be default.
            for existing_slice in subscriber["slice"]:
                existing_slice["default_indicator"] = False

        else:
            slice_data["default_indicator"] = False

    subscriber["slice"].append(slice_data)

    response = client.update_subscriber(
        imsi,
        subscriber
    )

    return json.loads(response)


def delete_slice(imsi, sst):
    client = Open5GSClient()
    client.login()

    subscriber_text = client.get_subscriber(imsi)
    subscriber = json.loads(subscriber_text)

    slices = subscriber.get("slice", [])

    # Find the slice that is going to be deleted.
    slice_to_delete = None

    for slice_item in slices:
        if slice_item.get("sst") == sst:
            slice_to_delete = slice_item
            break

    if slice_to_delete is None:
        raise ValueError(
            f"Slice with SST {sst} does not exist "
            f"for subscriber {imsi}."
        )

    deleted_was_default = (
        slice_to_delete.get("default_indicator", False)
    )

    # Remove the requested slice.
    remaining_slices = [
        slice_item
        for slice_item in slices
        if slice_item.get("sst") != sst
    ]

    # If the deleted slice was the default and other slices remain,
    # make the first remaining slice the new default.
    if deleted_was_default and remaining_slices:

        for index, slice_item in enumerate(remaining_slices):
            slice_item["default_indicator"] = (
                index == 0
            )

    subscriber["slice"] = remaining_slices

    response = client.update_subscriber(
        imsi,
        subscriber
    )

    return json.loads(response)


def update_slice(imsi, sst, default_indicator):
    client = Open5GSClient()
    client.login()

    subscriber_text = client.get_subscriber(imsi)
    subscriber = json.loads(subscriber_text)

    slices = subscriber.get("slice", [])

    slice_found = False

    for slice_item in slices:

        if slice_item.get("sst") == sst:

            slice_found = True

            slice_item["default_indicator"] = (
                default_indicator
            )

    if not slice_found:
        raise ValueError(
            f"Slice with SST {sst} does not exist "
            f"for subscriber {imsi}."
        )

    # If a slice is being made default, make every other
    # slice non-default.
    if default_indicator is True:

        for slice_item in slices:

            if slice_item.get("sst") != sst:
                slice_item["default_indicator"] = False

    # Make sure that if there are slices, at least one
    # remains default.
    elif slices:

        has_default = any(
            slice_item.get("default_indicator", False)
            for slice_item in slices
        )

        if not has_default:
            slices[0]["default_indicator"] = True

    subscriber["slice"] = slices

    response = client.update_subscriber(
        imsi,
        subscriber
    )

    return json.loads(response)
