import requests
import datetime

from django.conf import settings


class Monta:
    def __init__(self):
        self.client_secret = settings.MONTA_CLIENT_SECRET
        self.client_id = settings.MONTA_CLIENT_ID
        self.domain = "https://public-api.monta.com/api/v1"
        self.access_token = None
        self.refresh_token = None
        self.expires_at = 0

    @staticmethod
    def parse_monta_date(date_str: str) -> datetime:

        if date_str.endswith("Z"):
            date_str = date_str[:-1]

        if "." in date_str:
            main_part, fractional = date_str.split(".", 1)
            fractional = fractional[:6]
            date_str = f"{main_part}.{fractional}"

        return datetime.datetime.fromisoformat(f"{date_str}+00:00")

    def _get_token(self):
        now = datetime.datetime.now(datetime.timezone.utc)

        if self.access_token and now < self.expires_at:
            return self.access_token

        res = requests.post(
            f"{self.domain}/auth/token",
            json={
                "clientId": self.client_id,
                "clientSecret": self.client_secret,
            },
        )

        res.raise_for_status()
        data = res.json()

        self.access_token = data.get("accessToken")
        self.expires_at = self.parse_monta_date(data.get("accessTokenExpirationDate"))

        return self.access_token

    def request(self, method: str, endpoint: str, **kwargs):
        token = self._get_token()

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"

        return requests.request(
            method, f"{self.domain}/{endpoint}", headers=headers, **kwargs
        )

    def get(self, endpoint: str, **kwargs) -> requests.Response:
        return self.request("GET", endpoint, **kwargs)
