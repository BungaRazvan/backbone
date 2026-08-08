import pytest
from datetime import date
from decimal import Decimal

from mytools.models import Bill, Electricity, Gas, Seg


class TestBillsStatsView:
    URL = "/mytools/bills-stats"

    def test_returns_monthly_costs_and_usage(self, client):
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

        Gas.objects.create(
            g_bill=bill,
            g_from_date=date(2026, 5, 15),
            g_to_date=date(2026, 6, 15),
            g_kwh_used=Decimal("50.00"),
            g_unit_rate=Decimal("0.40"),
            g_subtotal_before_vat=Decimal("16.00"),
            g_standing_charge_rate=Decimal("0.05"),
            g_standing_charge_total=Decimal("2.75"),
            g_total_cost=Decimal("20.75"),
        )

        Seg.objects.create(
            s_bill=bill,
            s_from_date=date(2026, 5, 15),
            s_to_date=date(2026, 6, 15),
            s_kwh_used=Decimal("15.00"),
            s_unit_rate=Decimal("0.10"),
            s_total_cost=Decimal("5.40"),
        )

        response = client.get(
            self.URL,
            {"statsYear": "2026"},
            HTTP_X_API_KEY="test-token",
        )

        assert response.status_code == 200
        assert response.json() == [
            {
                "month": "Jun 2026",
                "b_date": "2026-06-15",
                "b_provider": "EDF",
                "costs": {
                    "electricity": 10.5,
                    "gas": 20.75,
                    "seg": 5.4,
                },
                "usage": {
                    "electricity": 100.0,
                    "gas": 50.0,
                    "seg": 15.0,
                },
            }
        ]

    def test_requires_mytools_api_token(self, client):
        response = client.get(self.URL, {"statsYear": "2026"})

        assert response.status_code == 403
        assert response.content.decode() == "Missing API token"
