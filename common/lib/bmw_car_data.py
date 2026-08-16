import json
import logging
import time
from typing import Any, Dict, Optional
import requests
from django.conf import settings


class BMWCarDataClient:
    """Standalone client to handle BMW CarData OAuth device authentication and requests."""

    GCDM_BASE_URL = "https://customer.bmwgroup.com/gcdm/oauth"
    CARDATA_BASE_URL = "https://api-cardata.bmwgroup.com"

    DEFAULT_SCOPE = "openid cardata:api:read cardata:streaming:read"

    def __init__(self):
        self.client_id = settings.BMW_CAR_DATA_CLIENT_ID
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.id_token: Optional[str] = None
        self.device_code: Optional[str] = None
        self.expires_at: Optional[float] = None

    def request_device_code(self, scope: Optional[str] = None) -> Dict[str, Any]:
        """Step 1: Initiate OAuth Device Authorization Grant."""
        url = f"{self.GCDM_BASE_URL}/device/code"
        payload = {
            "client_id": self.client_id,
            "response_type": "device_code",
            "scope": scope or self.DEFAULT_SCOPE,
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        response = requests.post(url, data=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        self.device_code = data.get("device_code")

        return data

    def get_tokens_from_device_code(
        self, device_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """Step 2: Exchange approved device_code for access and refresh tokens."""

        target_device_code = device_code or self.device_code

        if not target_device_code:
            raise ValueError(
                "No device code available. Call request_device_code first."
            )

        url = f"{self.GCDM_BASE_URL}/token"
        payload = {
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "client_id": self.client_id,
            "device_code": target_device_code,
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        response = requests.post(url, data=payload, headers=headers, timeout=10)
        print(response.json(), "--------------")

        response.raise_for_status()
        data = response.json()
        self._update_token_state(data)
        return data

    def refresh_access_token(
        self, refresh_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Step 3: Generate a fresh access_token using a refresh_token."""

        target_refresh_token = refresh_token or self.refresh_token

        if not target_refresh_token:
            raise ValueError("No refresh token available.")

        url = f"{self.GCDM_BASE_URL}/token"
        payload = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "refresh_token": target_refresh_token,
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        response = requests.post(url, data=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        self._update_token_state(data)
        return data

    def _update_token_state(self, token_data: Dict[str, Any]) -> None:
        """Internal helper to set tokens and calculate expiration timestamp."""
        self.access_token = token_data.get("access_token")

        if "refresh_token" in token_data:
            self.refresh_token = token_data["refresh_token"]

        expires_in = token_data.get("expires_in", 3600)
        self.expires_at = time.time() + expires_in - 60

    def ensure_valid_token(self) -> str:
        """Ensures access token is available and active. Refreshes or requests device code if expired."""

        # 1. Active access_token is valid
        if self.access_token and self.expires_at and time.time() < self.expires_at:
            return self.access_token

        # 2. Try refreshing if refresh_token exists
        if self.refresh_token:
            try:
                self.refresh_access_token()
                if self.access_token:
                    return self.access_token
            except requests.RequestException:
                pass  # Refresh failed or token revoked, fallback to device authorization

        # 3. Fallback: Obtain tokens via device_code
        if self.device_code:
            self.get_tokens_from_device_code()

            if self.access_token:
                return self.access_token

        # 4. Initiate a fresh device authorization flow
        device_data = self.request_device_code()
        raise PermissionError(
            f"Authentication required. Please open {device_data.get('verification_uri')} "
            f"and enter user code: {device_data.get('user_code')}"
        )

    def ensure_valid_id_token(self) -> str:
        """Ensures a valid ID token is available by polling until linked."""
        # 1. Return active id_token if not expired
        if self.id_token and self.expires_at and time.time() < self.expires_at:
            return self.id_token

        # 2. Refresh using refresh_token if available
        if self.refresh_token:
            try:
                self.refresh_access_token()
                if self.id_token:
                    return self.id_token
            except requests.RequestException:
                pass

        # 3. Fallback: Initiate Device Authorization and poll until linked
        device_data = self.request_device_code()
        device_code = device_data.get("device_code")
        print(device_data)
        while True:
            print("here")
            try:
                data = self.get_tokens_from_device_code(device_code)
                print(data)
                return data.get("id_token")
            except requests.RequestException:
                time.sleep(device_data.get("interval"))

    def request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:

        access_token = self.ensure_valid_token()

        _headers = kwargs.pop("headers", {})
        headers = {
            "Authorization": f"Bearer {access_token}",
            "x-version": "v1",
            "Accept": "application/json",
        }
        headers.update(_headers)

        return requests.request(
            method, f"{self.CARDATA_BASE_URL}/{endpoint}", headers=headers, **kwargs
        )

    def get(self, endpoint: str, **kwargs) -> requests.Response:
        return self.request("GET", endpoint, **kwargs)
