import requests
import hashlib
import time

from django.conf import settings


class FoxCloud:
    def __init__(self):
        self.token = settings.FOX_CLOUD_API_KEY
        self.domain = "https://www.foxesscloud.com/"

    def get_signature(self, path: str) -> tuple[str, str]:
        """Generate API signature for authentication."""

        if not path.startswith("/"):
            path = f"/{path}"

        timestamp = str(int(time.time() * 1000))
        signature_string = rf"{path}\r\n{self.token}\r\n{timestamp}"
        signature = hashlib.md5(signature_string.encode("UTF-8")).hexdigest()
        return signature, timestamp

    def get_headers(self, path: str) -> dict:
        """Generate request headers with authentication."""

        signature, timestamp = self.get_signature(path)

        return {
            "content-Type": "application/json",
            "token": self.token,
            "timestamp": timestamp,
            "signature": signature,
            "lang": "en",
        }

    def call_fox_api(self, path, payload=None):
        """
        Signs and posts requests natively to FoxESS Cloud using standard requests.
        Enforces the mandatory leading slash required by the FoxESS authentication engine.
        """

        url = self.domain + path
        response = requests.post(url, headers=self.get_headers(path), json=payload)
        response.raise_for_status()
        return response.json()
