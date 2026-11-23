from src.open5gs.rest_client import Open5GSClient


test_subscriber = {
    "imsi": "001010000000999",
    "security": {
        "k": "465B5CE8 B199B49F AA5F0A2E E238A6BC",
        "amf": "8000",
        "opc": "E8ED289D EBA952E4 283B54E8 8E6183CA",
    },
    "ambr": {
        "downlink": {"value": 1, "unit": 3},
        "uplink": {"value": 1, "unit": 3},
    },
    "slice": [
        {
            "sst": 1,
            "default_indicator": True,
            "session": [
                {
                    "name": "internet",
                    "type": 3,
                    "qos": {
                        "index": 9,
                        "arp": {
                            "priority_level": 8,
                            "pre_emption_capability": 1,
                            "pre_emption_vulnerability": 1,
                        },
                    },
                    "ambr": {
                        "downlink": {"value": 1, "unit": 3},
                        "uplink": {"value": 1, "unit": 3},
                    },
                }
            ],
        }
    ],
}


def main():
    client = Open5GSClient()
    client.login()
    print(client.add_subscriber(test_subscriber))


if __name__ == "__main__":
    main()
