import requests

session = requests.Session()

base_url = "http://localhost:9999/api"

csrf = session.get(
    f"{base_url}/auth/csrf"
).json()["csrfToken"]

login = session.post(
    f"{base_url}/auth/login",
    json={
        "username": "admin",
        "password": "1423"
    },
    headers={
        "X-CSRF-Token": csrf
    },
    allow_redirects=False
)

print("LOGIN:", login.status_code)

session_info = session.get(
    f"{base_url}/auth/session"
).json()

jwt = session_info["authToken"]
csrf = session_info["csrfToken"]

payload = {
    "imsi": "001010000001234",
    "ambr": {
        "downlink": {
            "value": 1,
            "unit": 3
        },
        "uplink": {
            "value": 1,
            "unit": 3
        }
    },
    "security": {
        "k": "465B5CE8 B199B49F AA5F0A2E E238A6BC",
        "amf": "8000",
        "opc": "E8ED289D EBA952E4 283B54E8 8E6183CA"
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
                            "pre_emption_vulnerability": 1
                        }
                    }
                }
            ]
        }
    ]
}

response = session.post(
    f"{base_url}/db/subscriber",
    json=payload,
    headers={
        "Authorization": f"Bearer {jwt}",
        "X-CSRF-Token": csrf
    },
    timeout=15
)

print("STATUS:", response.status_code)
print("TEXT:", response.text)
