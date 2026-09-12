from datetime import date

import pytest
from mytools.models import InverterDataPoint


@pytest.fixture
def setup_test_data(db):

    InverterDataPoint.objects.create(
        idp_date=date(2025, 6, 15),
        idp_solar_generation_kwh=12.0,
        idp_grid_export_kwh=2.0,
        idp_grid_import_kwh=4.0,
        idp_home_consumption_kwh=10.0,
        idp_battery_charge_kwh=3.0,
        idp_battery_discharge_kwh=2.0,
    )

    InverterDataPoint.objects.create(
        idp_date=date(2025, 7, 15),
        idp_solar_generation_kwh=15.0,
        idp_grid_export_kwh=3.0,
        idp_grid_import_kwh=5.0,
        idp_home_consumption_kwh=12.0,
        idp_battery_charge_kwh=4.0,
        idp_battery_discharge_kwh=3.0,
    )


class TestSolarGenerationView:
    URL = "/mytools/solar/generation"

    def test_returns_aggregated_solar_generation_for_year(
        self, client, setup_test_data
    ):
        response = client.get(
            self.URL,
            {"statsYear": "2025"},
            HTTP_X_API_KEY="test-token",
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        assert data[0]["month"] == "Jun"
        assert data[0]["generated_energy"] == 12.0
        assert data[0]["consumed_energy"] == 10.0
        assert data[1]["month"] == "Jul"
        assert data[1]["generated_energy"] == 15.0
        assert data[1]["consumed_energy"] == 12.0
        assert data[1]["month"] == "Jul"
        assert data[1]["generated_energy"] == 15.0
        assert data[1]["consumed_energy"] == 12.0

    def test_no_api_key_returns_401(self, client):
        response = client.get(self.URL, {"statsYear": "2025"})
        assert response.status_code == 401
