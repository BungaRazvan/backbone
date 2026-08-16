import time

from rest_framework import status


from mytools.views.bmw_car_data.utils import (
    COOKIE_ACCESS_TOKEN,
    COOKIE_REFRESH_TOKEN,
    COOKIE_EXPIRES_AT,
)
from common.lib.bmw_car_data import BMWCarDataClient


class TestBMWCarDataContainersView:
    """Test BMW Car Data containers view"""

    URL = "/mytools/bmw/cardata/containers"

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

    def test_get_all_containers_success(self, client, mock_requests):
        """Test successful retrieval of all containers"""

        mock_requests(
            "common.lib.bmw_car_data",
            responses={
                f"{BMWCarDataClient.CARDATA_BASE_URL}/customers/containers": (
                    {
                        "status": 200,
                        "json": [
                            {"containerId": "container1", "name": "Main Container"},
                            {
                                "containerId": "container2",
                                "name": "Secondary Container",
                            },
                        ],
                    }
                )
            },
        )
        self._set_cookies(client)

        response = client.get(
            self.URL,
            HTTP_X_API_KEY="test-token",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Main Container"

    def test_get_single_container_success(self, client, mock_requests):
        """Test successful retrieval of single container"""

        mock_requests(
            "common.lib.bmw_car_data",
            responses={
                f"{BMWCarDataClient.CARDATA_BASE_URL}/customers/containers/container1": (
                    {
                        "status": 200,
                        "json": {
                            "containerId": "container1",
                            "name": "Main Container",
                            "technicalDescriptors": ["desc1", "desc2"],
                        },
                    }
                )
            },
        )

        self._set_cookies(client)

        response = client.get(
            self.URL,
            {"containerId": "container1"},
            HTTP_X_API_KEY="test-token",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["containerId"] == "container1"

    def test_post_container_success(self, client, mock_requests):
        """Test successful container creation"""

        mock_requests(
            "common.lib.bmw_car_data",
            responses={
                f"{BMWCarDataClient.CARDATA_BASE_URL}/customers/containers": (
                    {"status": 201, "json": {"containerId": "new_container"}}
                )
            },
        )

        self._set_cookies(client)

        response = client.post(
            self.URL,
            {
                "name": "New Container",
                "purpose": "Testing",
                "technicalDescriptors": ["desc1", "desc2"],
            },
            HTTP_X_API_KEY="test-token",
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.json()
        assert data["containerId"] == "new_container"

    def test_post_container_invalid_cookies(self, client, mocker):
        """Test POST request with invalid cookies"""

        response = client.post(
            self.URL,
            {
                "name": "Test",
                "purpose": "Testing",
                "technicalDescriptors": ["desc1"],
            },
            HTTP_X_API_KEY="test-token",
            content_type="application/json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_post_container_api_error_with_response(self, client, mock_requests):
        """Test POST with API error response containing JSON"""

        mock_requests(
            "common.lib.bmw_car_data",
            responses={
                f"{BMWCarDataClient.CARDATA_BASE_URL}/customers/containers": (
                    {"status": 400, "json": {"error": "Invalid container name"}}
                )
            },
        )

        self._set_cookies(client)

        response = client.post(
            self.URL,
            {
                "name": "aaa",
                "purpose": "Testing",
                "technicalDescriptors": ["desc1"],
            },
            HTTP_X_API_KEY="test-token",
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_post_container_api_error(self, client, mock_requests):
        """Test POST with API error but no response body"""

        mock_requests(
            "common.lib.bmw_car_data",
            responses={
                f"{BMWCarDataClient.CARDATA_BASE_URL}/customers/containers": (
                    {"status": 502, "json": {"error": "Bad Gateway"}}
                )
            },
        )

        self._set_cookies(client)

        response = client.post(
            self.URL,
            {
                "name": "Test",
                "purpose": "Testing",
                "technicalDescriptors": ["desc1"],
            },
            HTTP_X_API_KEY="test-token",
            content_type="application/json",
        )

        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        data = response.json()
        assert "error" in data

    def test_delete_container_success(self, client, mock_requests):
        """Test successful container deletion"""

        mock_requests(
            "common.lib.bmw_car_data",
            responses={
                f"{BMWCarDataClient.CARDATA_BASE_URL}/customers/containers/container1": (
                    {"status": 200, "json": {"status": "deleted"}}
                )
            },
        )

        self._set_cookies(client)

        response = client.delete(
            self.URL,
            {"containerId": "container1"},
            HTTP_X_API_KEY="test-token",
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"

    def test_delete_container_invalid_cookies(self, client):
        """Test DELETE request with invalid cookies"""

        response = client.delete(
            self.URL,
            {"containerId": "container1"},
            HTTP_X_API_KEY="test-token",
            content_type="application/json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_container_not_found(self, client, mock_requests):
        """Test DELETE with container not found"""

        self._set_cookies(client)

        mock_requests(
            "common.lib.bmw_car_data",
            responses={
                f"{BMWCarDataClient.CARDATA_BASE_URL}/customers/containers/nonexistent": (
                    {"status": 404, "json": {"error": "Container not found"}}
                )
            },
        ),

        response = client.delete(
            self.URL,
            {"containerId": "nonexistent"},
            HTTP_X_API_KEY="test-token",
            content_type="application/json",
        )

        assert response.status_code == 404
        data = response.json()

        assert (
            data["error"]
            == "404 Client Error: HTTP Error for url: https://api-cardata.bmwgroup.com/customers/containers/nonexistent"
        )
