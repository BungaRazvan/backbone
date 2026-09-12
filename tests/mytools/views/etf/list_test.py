from freezegun import freeze_time


class TestEtfsListView:
    URL = "/mytools/etfs/list"

    def test_returns_403(self, client):
        response = client.get(self.URL)
        assert response.status_code == 403

    @freeze_time("2024-06-20")
    def test_returns_etfs_list(self, client, setup_test_data):
        response = client.get(self.URL, HTTP_X_API_KEY="test-token")
        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        assert data[0]["ef_name"] == "Test ETF"
        assert data[1]["ef_name"] == "Another ETF"

        assert data[0]["recent_event"] is None
        assert data[1]["recent_event"] is None

        assert data[0]["shares"] == [
            {
                "efs_id": 1,
                "efs_amount": "100.00000000",
                "efs_purchase_date": "2025-01-10",
                "efs_funds": "salary",
                "efs_total_price": "1000.00000000",
            }
        ]
        assert data[1]["shares"] == [
            {
                "efs_id": 2,
                "efs_amount": "200.00000000",
                "efs_purchase_date": "2025-04-10",
                "efs_funds": "dividents",
                "efs_total_price": "2000.00000000",
            }
        ]

        assert data[0]["future_event"] == {
            "ee_id": 1,
            "ee_ex_date": "2025-01-15",
            "ee_payment_date": "2025-01-20",
            "ee_ex_estimated": False,
            "ee_payment_estimated": False,
            "ee_pay_per_share": "0.50000000",
            "ee_eligible_shares_amount": "100",
        }
