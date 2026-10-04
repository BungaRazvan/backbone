import pytest
from datetime import date
from decimal import Decimal

from mytools.models import BillingCycle, InverterDataPoint, TariffPeriod
from mytools.services.parse_bill.parameters import UtilityCategory


@pytest.fixture
def setup_test_data(db):
    TariffPeriod.objects.create(
        tp_provider_name="EDF",
        tp_tariff_name="Test Tariff",
        tp_start_date=date(2025, 1, 1),
        tp_end_date=date(2025, 12, 31),
        tp_standard_import_rate=Decimal("0.20756"),
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


class TestSolarPerformanceView:
    URL = "/mytools/solar/performance"

    def test_monthly_billing_cycle_excludes_end_date(self, client, setup_test_data):
        year = date.today().year
        BillingCycle.objects.create(
            start_date=date(year, 1, 1),
            end_date=None,
            cycle_day=26,
            type="monthly",
            category=UtilityCategory.ELECTRICITY.value,
        )
        TariffPeriod.objects.create(
            tp_provider_name="EDF",
            tp_tariff_name="Current Test Tariff",
            tp_start_date=date(year, 1, 1),
            tp_end_date=date(year, 12, 31),
            tp_standard_import_rate=Decimal("0.2000"),
            tp_standard_export_rate=Decimal("0.1500"),
            tp_standing_charge_rate=Decimal("0.1000"),
            tp_has_variable_rates=False,
        )

        for point_date, grid_import, grid_export in (
            (date(year, 6, 26), 1.0, 2.0),
            (date(year, 7, 25), 3.0, 4.0),
            (date(year, 7, 26), 100.0, 100.0),
        ):
            InverterDataPoint.objects.create(
                idp_date=point_date,
                idp_solar_generation_kwh=0.0,
                idp_grid_export_kwh=grid_export,
                idp_grid_import_kwh=grid_import,
                idp_home_consumption_kwh=0.0,
                idp_battery_charge_kwh=0.0,
                idp_battery_discharge_kwh=0.0,
            )

        response = client.get(
            self.URL,
            {"statsPeriodType": "month", "statsPeriod": "7"},
            HTTP_X_API_KEY="test-token",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["grid_import"] == pytest.approx(104.0)
        assert data["grid_export"] == pytest.approx(106.0)
        assert data["total_net_cost"] == pytest.approx(20.8)
        assert data["total_exported_revenue"] == pytest.approx(15.9)

    def test_returns_aggregated_energy_and_financials_for_year(
        self, client, setup_test_data
    ):

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
        assert data["total_gross_cost"] == pytest.approx(2.0756)
        assert data["total_net_cost"] == pytest.approx(0.83024)
        assert data["total_exported_revenue"] == pytest.approx(0.1)
        assert data["savings"] == pytest.approx(1.25)
        assert data["rte_percentage"] == pytest.approx(66.67)

    def test_no_api_key_returns_403(self, client):
        response = client.get(
            self.URL, {"statsPeriodType": "year", "statsPeriod": "2025"}
        )
        assert response.status_code == 403
