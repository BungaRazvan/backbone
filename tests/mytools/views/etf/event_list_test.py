import pytest
from freezegun import freeze_time


class TestEtfEventListView:
    URL = "/mytools/etfs/events"

    def test_returns_403(self, client):
        response = client.get(self.URL)
        assert response.status_code == 403

    @freeze_time("2025-06-20")
    def test_returns_etf_events(self, client, setup_test_data):
        response = client.get(self.URL, HTTP_X_API_KEY="test-token")
        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        assert data[0]["ee_ex_date"] == "2025-01-15"
        assert data[0]["ee_payment_date"] == "2025-01-20"
        assert data[1]["ee_ex_date"] == "2025-04-15"
        assert data[1]["ee_payment_date"] == "2025-04-20"
        assert data[0]["ee_eligible_shares_amount"] == "100"
        assert data[1]["ee_eligible_shares_amount"] == "200"
        assert data[0]["ee_ex_estimated"] is False
        assert data[0]["ee_payment_estimated"] is False
        assert data[1]["ee_ex_estimated"] is False
        assert data[1]["ee_payment_estimated"] is False
