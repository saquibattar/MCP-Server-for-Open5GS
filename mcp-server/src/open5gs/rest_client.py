import requests
import json
import os



class Open5GSClient:

    def __init__(self):
        self.base_url = "http://localhost:9999/api"
        self.session = requests.Session()
        self.jwt_token = None
        self.csrf_token = None


        self.username = os.environ.get("OPEN5GS_USERNAME")
        self.password = os.environ.get("OPEN5GS_PASSWORD")

        if not self.username or not self.password:
            raise RuntimeError(
                "OPEN5GS_USERNAME and OPEN5GS_PASSWORD must be configured."
            )


    def login(self):

        try:
            csrf_response = self.session.get(
                f"{self.base_url}/auth/csrf",
                timeout=10
            )
            csrf_response.raise_for_status()

            initial_csrf = csrf_response.json()["csrfToken"]

            login_response = self.session.post(
                f"{self.base_url}/auth/login",
                json={
                    "username": self.username,
                    "password": self.password
                },
                headers={
                    "X-CSRF-Token": initial_csrf
                },
                allow_redirects=False,
                timeout=10
            )
            login_response.raise_for_status()

            session_response = self.session.get(
                f"{self.base_url}/auth/session",
                timeout=10
            )
            session_response.raise_for_status()

            session_json = session_response.json()

            self.jwt_token = session_json.get("authToken")
            self.csrf_token = session_json.get("csrfToken")

            if not self.jwt_token:
                raise RuntimeError(
                    "Open5GS login succeeded but no authentication token was returned."
                )

        except requests.RequestException as e:
            raise RuntimeError(
                f"Open5GS management API is unavailable: {e}"
            ) from e

        except (KeyError, ValueError) as e:
            raise RuntimeError(
                "Open5GS returned an invalid authentication response."
            ) from e

    def list_subscribers(self):
        response = self.session.get(
            f"{self.base_url}/db/subscriber",
            headers={
                "Authorization": f"Bearer {self.jwt_token}"
            },
            timeout=10
        )

        response.raise_for_status()

        return response.text

    def get_subscriber(self, imsi):
        response = self.session.get(
            f"{self.base_url}/db/subscriber/{imsi}",
            headers={
                "Authorization": f"Bearer {self.jwt_token}"
            },
            timeout=10
        )

        response.raise_for_status()

        return response.text


    def add_subscriber(self, subscriber):
        response = self.session.post(
            f"{self.base_url}/db/subscriber",
            json=subscriber,
            headers={
                "Authorization": f"Bearer {self.jwt_token}",
                "X-CSRF-Token": self.csrf_token
            },
            timeout=10
        )

        response.raise_for_status()

        # Log only safe metadata; never log credentials or full responses.
        print(
            "Open5GS subscriber creation request completed:",
            f"status={response.status_code}",
            f"imsi={subscriber.get('imsi', 'unknown')}"
        )

        return response.text

    def update_subscriber(self, imsi, subscriber):
        response = self.session.put(
            f"{self.base_url}/db/subscriber/{imsi}",
            json=subscriber,
            headers={
                "Authorization": f"Bearer {self.jwt_token}",
                "X-CSRF-Token": self.csrf_token
            },
            timeout=10
        )

        response.raise_for_status()

        return response.text

    def delete_subscriber(self, imsi):
        response = self.session.delete(
            f"{self.base_url}/db/subscriber/{imsi}",
            headers={
                "Authorization": f"Bearer {self.jwt_token}",
                "X-CSRF-Token": self.csrf_token
            },
            timeout=10
        )

        response.raise_for_status()

        return response.text
