from datetime import date

from freezegun import freeze_time
import pytest
from decimal import Decimal
from mytools.models import Bill, Electricity, Seg, BillingCycle, Gas


@pytest.fixture
def setup_test_data(db):
    bill = Bill.objects.create(b_date=date(2026, 6, 15), b_provider="EDF")

    Electricity.objects.create(
        e_bill=bill,
        e_from_date=date(2026, 5, 15),
        e_to_date=date(2026, 6, 15),
        e_kwh_used=Decimal("100.00"),
        e_unit_rate=Decimal("0.20"),
        e_total_cost=Decimal("10.50"),
        e_subtotal_before_vat=Decimal("8.75"),
        e_standing_charge_rate=Decimal("0.10"),
        e_standing_charge_total=Decimal("1.50"),
    )

    Seg.objects.create(
        s_bill=bill,
        s_from_date=date(2026, 5, 15),
        s_to_date=date(2026, 6, 15),
        s_kwh_used=Decimal("15.00"),
        s_unit_rate=Decimal("0.10"),
        s_total_cost=Decimal("5.40"),
    )


class TestElectricityCostView:
    URL = "/mytools/bills/electricity_costs"

    def test_no_token_returns_403(self, client):
        response = client.get(self.URL)
        assert response.status_code == 403

    @freeze_time("2026-06-15")
    def test_no_billing_cycle_returns_404(self, client, setup_test_data):

        response = client.get(
            self.URL, {"statsPeriod": "6"}, HTTP_X_API_KEY="test-token"
        )
        assert response.status_code == 404

    @freeze_time("2026-08-27")
    def test_returns_costs_for_multiple_electricity_periods_in_a_cycle(
        self, client, db
    ):
        BillingCycle.objects.create(
            type="monthly",
            category="electricity",
            cycle_day=26,
            start_date=date(2023, 10, 2),
            end_date=None,
        )
        bill = Bill.objects.create(b_date=date(2026, 8, 27), b_provider="EDF")

        for from_date, to_date, usage, subtotal, standing_charge in (
            (
                date(2026, 7, 26),
                date(2026, 7, 31),
                "3.57",
                "3.57",
                "2.83",
            ),
            (
                date(2026, 8, 1),
                date(2026, 8, 25),
                "27.01",
                "21.65",
                "15.33",
            ),
        ):
            Electricity.objects.create(
                e_bill=bill,
                e_from_date=from_date,
                e_to_date=to_date,
                e_kwh_used=Decimal(usage),
                e_unit_rate=Decimal("0.20"),
                e_total_cost=Decimal(subtotal),
                e_subtotal_before_vat=Decimal(subtotal),
                e_standing_charge_rate=Decimal("0.10"),
                e_standing_charge_total=Decimal(standing_charge),
            )

        response = client.get(
            self.URL, {"statsPeriod": "8"}, HTTP_X_API_KEY="test-token"
        )

        assert response.status_code == 200
        assert response.json() == {
            "grid_import": 30.58,
            "grid_export": 0.0,
            "total_exported_revenue": 0.0,
            "savings": -7.06,
            "total_net_cost": 7.06,
        }

    @freeze_time("2026-06-15")
    def test_no_electricity_bills_returns_404(self, client, db):
        BillingCycle.objects.create(
            type="monthly",
            category="electricity",
            cycle_day=15,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 31),
        )

        response = client.get(
            self.URL, {"statsPeriod": "6"}, HTTP_X_API_KEY="test-token"
        )
        assert response.status_code == 404

    @freeze_time("2026-06-15")
    def test_returns_electricity_costs(self, client, setup_test_data):
        BillingCycle.objects.create(
            type="monthly",
            category="electricity",
            cycle_day=15,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 31),
        )

        response = client.get(
            self.URL, {"statsPeriod": "6"}, HTTP_X_API_KEY="test-token"
        )
        assert response.status_code == 200
        assert response.json() == {
            "grid_import": 100.0,
            "grid_export": 15.0,
            "total_exported_revenue": 5.4,
            "savings": -7.25,
            "total_net_cost": 7.25,
        }

        @freeze_time("2026-06-15")
        def test_returns_electricity_costs_with_no_seg_bills(self, client, db):
            BillingCycle.objects.create(
                type="monthly",
                category="electricity",
                cycle_day=15,
                start_date=date(2026, 5, 1),
                end_date=date(2026, 5, 31),
            )

            bill = Bill.objects.create(b_date=date(2026, 6, 15), b_provider="EDF")

            Electricity.objects.create(
                e_bill=bill,
                e_from_date=date(2026, 5, 15),
                e_to_date=date(2026, 6, 15),
                e_kwh_used=Decimal("100.00"),
                e_unit_rate=Decimal("0.20"),
                e_total_cost=Decimal("10.50"),
                e_subtotal_before_vat=Decimal("8.75"),
                e_standing_charge_rate=Decimal("0.10"),
                e_standing_charge_total=Decimal("1.50"),
            )

            response = client.get(
                self.URL, {"statsPeriod": "6"}, HTTP_X_API_KEY="test-token"
            )
            assert response.status_code == 200
            assert response.json() == {
                "grid_import": 100.0,
                "grid_export": 0.0,
                "total_exported_revenue": 0.0,
                "savings": -10.5,
                "total_net_cost": 10.5,
            }

            @freeze_time("2026-06-15")
            def test_returns_electricity_costs_with_no_electricity_bills(
                self, client, db
            ):
                BillingCycle.objects.create(
                    type="monthly",
                    category="electricity",
                    cycle_day=15,
                    start_date=date(2026, 5, 1),
                    end_date=date(2026, 5, 31),
                )

                Seg.objects.create(
                    s_bill=Bill.objects.create(
                        b_date=date(2026, 6, 15), b_provider="EDF"
                    ),
                    s_from_date=date(2026, 5, 15),
                    s_to_date=date(2026, 6, 15),
                    s_kwh_used=Decimal("15.00"),
                    s_unit_rate=Decimal("0.10"),
                    s_total_cost=Decimal("5.40"),
                )

                response = client.get(
                    self.URL, {"statsPeriod": "6"}, HTTP_X_API_KEY="test-token"
                )
                assert response.status_code == 404
