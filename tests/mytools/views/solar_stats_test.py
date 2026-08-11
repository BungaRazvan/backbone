import pytest
from datetime import date
from decimal import Decimal

from mytools.models import InverterDataPoint, TariffPeriod


class TestSolarStatsView:
    URL = "/mytools/solar-stats"

    def test_returns_aggregated_energy_and_financials_for_year(self, client):
        TariffPeriod.objects.create(
            tp_provider_name="EDF",
            tp_tariff_name="Test Tariff",
            tp_start_date=date(2025, 1, 1),
            tp_end_date=date(2025, 12, 31),
            tp_standard_import_rate=Decimal("0.15"),
            tp_standard_export_rate=Decimal("0.05"),
            tp_standing_charge_rate=Decimal("0.10"),
            tp_has_variable_rates=False,
        )

        InverterDataPoint.objects.create(
            idp_date=date(2025, 6, 15),
            idp_solar_generation_kwh=12.0,
            idp_grid_export_kwh=2.0,
            idp_grid_import_kwh=4.0,
            idp_home_consumption_kwh=10.0,
            idp_battery_charge_kwh=3.0,
            idp_battery_discharge_kwh=2.0,
        )

        response = client.get(
            self.URL,
            {"statsPeriodType": "year", "statsPeriod": "2025"},
            HTTP_X_API_KEY="test-token",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["battery_charge"] == 3.0
        assert data["battery_discharge"] == 2.0
        assert data["home_consumption"] == 10.0
        assert data["grid_import"] == 4.0
        assert data["grid_export"] == 2.0
        assert data["total_gross_cost"] == pytest.approx(1.5)
        assert data["total_net_cost"] == pytest.approx(0.6)
        assert data["total_exported_revenue"] == pytest.approx(0.1)
        assert data["savings"] == pytest.approx(0.9)
        assert data["rte_percentage"] == pytest.approx(66.67)
        assert data["total_standing_charge"] == pytest.approx(36.4)
