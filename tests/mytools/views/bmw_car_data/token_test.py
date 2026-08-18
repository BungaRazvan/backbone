import pytest
import time
from rest_framework import status

from common.lib.bmw_car_data import BMWCarDataClient
from mytools.views.bmw_car_data.utils import (
    COOKIE_ACCESS_TOKEN,
    COOKIE_REFRESH_TOKEN,
    COOKIE_EXPIRES_AT,
)
from tests.conftest import mock_requests


class TestBMWCarDataAuthTokenView:
    """Test BMW Car Data authentication token view"""

    URL = "/mytools/bmw/cardata/auth-token"

    def setup_method(self):
        """Set up test cookies"""

        self.valid_cookies = {
            COOKIE_ACCESS_TOKEN: "valid_access_token",
            COOKIE_REFRESH_TOKEN: "valid_refresh_token",
            COOKIE_EXPIRES_AT: str(time.time() + 3600),
        }

    def _set_cookies(self, client):
        """Helper to set cookies on client"""

        for key, value in self.valid_cookies.items():
            client.cookies[key] = value

    def test_post_token_with_valid_device_code(
        self,
        client,
        mock_requests,
    ):
        """Test token endpoint with valid device code"""

        mock_requests(
            "common.lib.bmw_car_data",
            responses={
                f"{BMWCarDataClient.GCDM_BASE_URL}/token": (
                    {
                        "status": 200,
                        "json": {
                            "access_token": "new_access_token",
                            "refresh_token": "new_refresh_token",
                            "expires_in": 3600,
                        },
                    }
                )
            },
        )

        response = client.post(
            self.URL,
            {"device_code": "test_device_code"},
            HTTP_X_API_KEY="test-token",
            content_type="application/json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"detail": "Authentificated succesfully"}
        # Verify that new tokens from API response are set as cookies
        assert response.cookies.get(COOKIE_ACCESS_TOKEN).value == "new_access_token"
        assert response.cookies.get(COOKIE_REFRESH_TOKEN).value == "new_refresh_token"
        # expires_at should be set to approximately current time + expires_in
        expires_at = float(response.cookies.get(COOKIE_EXPIRES_AT).value)
        assert expires_at > time.time()  # Token is valid in the future
        assert expires_at <= time.time() + 3600 + 10  # Within expected range (+ buffer)

    def test_post_token_with_valid_session(self, client, mock_requests):
        """Test token endpoint with valid session"""

        mock_requests(
            "common.lib.bmw_car_data",
            responses={
                f"{BMWCarDataClient.GCDM_BASE_URL}/token": (
                    {
                        "status": 200,
                        "json": {
                            "access_token": "new_access_token",
                            "refresh_token": "new_refresh_token",
                            "expires_in": 3600,
                        },
                    }
                )
            },
        )

        self._set_cookies(client)

        response = client.post(
            self.URL,
            {"device_code": "test_device_code"},
            HTTP_X_API_KEY="test-token",
            content_type="application/json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"detail": "Session already active and valid."}

    def test_post_token_with_refresh_token(self, client, mock_requests):
        """Test token refresh when access token expired"""

        mock_requests(
            "common.lib.bmw_car_data",
            responses={
                f"{BMWCarDataClient.GCDM_BASE_URL}/token": (
                    {
                        "status": 200,
                        "json": {
                            "access_token": "new_access_token",
                            "refresh_token": "new_refresh_token",
                            "expires_in": 3600,
                        },
                    }
                )
            },
        )

        self._set_cookies(client)
        client.cookies[COOKIE_EXPIRES_AT] = str(time.time() - 100)  # Expired token

        response = client.post(
            self.URL,
            {"device_code": "test_device_code"},
            HTTP_X_API_KEY="test-token",
            content_type="application/json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"detail": "Authentificated succesfully"}
        # Verify that new tokens from API response are set as cookies
        assert response.cookies.get(COOKIE_ACCESS_TOKEN).value == "new_access_token"
        assert response.cookies.get(COOKIE_REFRESH_TOKEN).value == "new_refresh_token"
        assert (
            float(response.cookies.get(COOKIE_EXPIRES_AT).value) > time.time()
        )  # Token is valid in the future

    def test_post_token_refresh_fails(self, client, mock_requests):
        """Test handling of failed token refresh"""

        mock_requests(
            "common.lib.bmw_car_data",
            responses={
                f"{BMWCarDataClient.GCDM_BASE_URL}/token": (
                    {
                        "status": 400,
                        "json": {"error": "Invalid refresh token"},
                    }
                )
            },
        )

        response = client.post(
            self.URL,
            {"device_code": "test_device_code"},
            HTTP_X_API_KEY="test-token",
            content_type="application/json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data

    def test_post_token_authentication_fails(self, client, mock_requests):
        """Test handling of failed token authentication"""

        mock_requests(
            "common.lib.bmw_car_data",
            responses={
                f"{BMWCarDataClient.GCDM_BASE_URL}/token": (
                    {
                        "status": 400,
                        "json": {"error": "Authentication failed"},
                    }
                )
            },
        )

        response = client.post(
            self.URL,
            {"device_code": "invalid_device_code"},
            HTTP_X_API_KEY="test-token",
            content_type="application/json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data
        assert (
            "Token authentication failed: 400 Client Error: HTTP Error for url: https://customer.bmwgroup.com/gcdm/oauth/token"
            in data["error"]
        )
