import copy
import json
from unittest.mock import Mock, patch

import pytest

from src.tools.qos import update_slice_qos
from src.open5gs.rest_client import Open5GSClient


IMSI = "001011234567895"
SST = 1


def make_subscriber(five_qi=9):
    return {
        "imsi": IMSI,
        "slice": [
            {
                "sst": SST,
                "default_indicator": True,
                "session": [
                    {
                        "name": "internet",
                        "qos": {
                            "index": five_qi,
                            "arp": {
                                "priority_level": 8,
                                "pre_emption_capability": 1,
                                "pre_emption_vulnerability": 1
                            }
                        },
                        "ambr": {
                            "downlink": {"value": 1, "unit": 2},
                            "uplink": {"value": 1, "unit": 2}
                        }
                    }
                ]
            }
        ]
    }


def setup_client(initial_subscriber, persisted_subscriber=None):
    client = Mock(spec=Open5GSClient)
    state = {"subscriber": copy.deepcopy(initial_subscriber)}

    def get_subscriber(imsi):
        return json.dumps(copy.deepcopy(state["subscriber"]))

    def update_subscriber(imsi, subscriber):
        state["subscriber"] = copy.deepcopy(subscriber)

        if persisted_subscriber is not None:
            state["subscriber"] = copy.deepcopy(persisted_subscriber)

        return {"status": "success"}

    client.get_subscriber.side_effect = get_subscriber
    client.update_subscriber.side_effect = update_subscriber

    return client, state


def test_update_slice_qos_ambr_only_preserves_5qi_and_arp():
    initial = make_subscriber(five_qi=9)
    client, state = setup_client(initial)

    with patch("src.tools.qos.Open5GSClient", return_value=client):
        result = update_slice_qos(IMSI, SST, 2, 2)

    session = state["subscriber"]["slice"][0]["session"][0]

    assert "error" not in result
    assert result["success"] is True
    assert result["updated_fields"]["ambr"] is True
    assert result["updated_fields"]["five_qi"] is False
    assert session["qos"]["index"] == 9
    assert session["ambr"]["downlink"] == {"value": 2, "unit": 2}
    assert session["ambr"]["uplink"] == {"value": 2, "unit": 2}
    assert session["qos"]["arp"] == {
        "priority_level": 8,
        "pre_emption_capability": 1,
        "pre_emption_vulnerability": 1
    }


def test_update_slice_qos_persists_and_verifies_5qi():
    initial = make_subscriber(five_qi=9)
    client, state = setup_client(initial)

    with patch("src.tools.qos.Open5GSClient", return_value=client):
        result = update_slice_qos(
            IMSI, SST, 2, 2, five_qi=7
        )

    session = state["subscriber"]["slice"][0]["session"][0]

    assert result["success"] is True
    assert result["verification_passed"] is True
    assert result["updated_fields"]["five_qi"] is True
    assert session["qos"]["index"] == 7
    assert session["qos"]["arp"] == {
        "priority_level": 8,
        "pre_emption_capability": 1,
        "pre_emption_vulnerability": 1
    }


def test_update_slice_qos_fails_when_5qi_readback_mismatches():
    initial = make_subscriber(five_qi=9)
    client, state = setup_client(
        initial,
        persisted_subscriber=make_subscriber(five_qi=9)
    )

    with patch("src.tools.qos.Open5GSClient", return_value=client):
        result = update_slice_qos(
            IMSI, SST, 2, 2, five_qi=7
        )

    assert result["success"] is False
    assert result["verification_passed"] is False
    assert result["requested_five_qi"] == 7
    assert result["actual_five_qi"] == 9


@pytest.mark.parametrize("invalid_five_qi", [0, 256, -1, 1.5, True])
def test_update_slice_qos_rejects_invalid_5qi(invalid_five_qi):
    client = Mock(spec=Open5GSClient)

    with patch("src.tools.qos.Open5GSClient", return_value=client):
        result = update_slice_qos(
            IMSI, SST, 2, 2, five_qi=invalid_five_qi
        )

    assert "error" in result
    client.update_subscriber.assert_not_called()
