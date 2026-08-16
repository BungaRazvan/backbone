from rest_framework import status


from common.lib.bmw_car_data import BMWCarDataClient


from rest_framework import status


class TestBMWCarDataAuthDeviceCodeView:
    """Test BMW Car Data authentication device code view"""

    URL = "/mytools/bmw/cardata/auth-device"

    def test_post_device_code_success(
        self,
        client,
        mock_requests,
    ):
        """Test successful device code request"""

        mock_requests(
            "common.lib.bmw_car_data",
            responses={
                f"{BMWCarDataClient.GCDM_BASE_URL}/device/code": (
                    {
                        "status": 200,
                        "json": {
                            "device_code": "test_device_code_123",
                            "user_code": "ABCD-1234",
                            "verification_uri": "https://example.com/verify",
                            "expires_in": 1800,
                        },
                    }
                )
            },
        )

        response = client.post(
            self.URL,
            {
                "scope": "profile",
            },
            HTTP_X_API_KEY="test-token",
            content_type="application/json",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        print(data)
        assert data["device_code"] == "test_device_code_123"
        assert data["user_code"] == "ABCD-1234"

    def test_post_device_code_without_scope(
        self,
        client,
        mock_requests,
    ):
        """Test device code request without optional scope"""

        mock_requests(
            "common.lib.bmw_car_data",
            responses={
                f"{BMWCarDataClient.GCDM_BASE_URL}/device/code": (
                    {
                        "method": "POST",
                        "status": 200,
                        "json": {
                            "device_code": "test_device_code_456",
                            "user_code": "EFGH-5678",
                            "verification_uri": "https://example.com/verify",
                            "expires_in": 1800,
                        },
                    }
                )
            },
        )

        response = client.post(
            self.URL,
            {},
            HTTP_X_API_KEY="test-token",
            content_type="application/json",
        )

        assert response.status_code == status.HTTP_200_OK
