import pytest
from freezegun import freeze_time


class TestEtfsMetricsView:
    URL = "/mytools/etfs/metrics"

    def test_returns_403(self, client):
        response = client.get(self.URL)
        assert response.status_code == 403

    @freeze_time("2024-06-20")
    def test_returns_etfs_metrics_no_dividends(self, client, setup_test_data):
        response = client.get(self.URL, HTTP_X_API_KEY="test-token")
        assert response.status_code == 200
        data = response.json()

        assert data["out_of_pocket"] == "1000.00000000"
        assert data["compounding_cost"] == "2000.00000000"
        assert data["cumulative_dividends"] == "0.00000000"
        assert data["dividends_this_month"] == "0.00000000"
        assert data["invested"] == "3000"
        assert data["dividend_roi"] == 0.0
