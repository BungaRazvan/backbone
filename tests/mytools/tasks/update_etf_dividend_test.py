import pytest


from datetime import date

from freezegun import freeze_time

from mytools.models import Etf, EtfEvent
from mytools.tasks.update_etf_dividend import update_dividend
from tests.mytools.tasks.utils import yahoo_dividends

pytestmark = pytest.mark.django_db(
    databases=["default", "mytools_db"],
)


@pytest.fixture
def etf(db):
    return Etf.objects.create(
        ef_symbol="VWR.L",
        ef_pay_lag_days=5,
        ef_distribution="quarterly",
    )


@freeze_time("2025-01-10")
def test_picks_future_ex_date(mock_requests, etf):
    mock_requests(
        "mytools.tasks.update_etf_dividend",
        responses={
            "finance.yahoo.com": {
                "json": yahoo_dividends(
                    {"date": "2024-12-15", "amount": 1.0},
                    {"date": "2025-03-15", "amount": 2.0},
                )
            }
        },
    )

    update_dividend(etf.ef_id)

    event = EtfEvent.objects.get(ee_etf=etf)
    assert event.ee_ex_date == date(2025, 3, 15)
    assert event.ee_ex_estimated is False


@freeze_time("2025-01-10")
def test_uses_latest_past_if_no_future(mock_requests, etf):
    mock_requests(
        "mytools.tasks.update_etf_dividend",
        responses={
            "finance.yahoo.com": {
                "json": yahoo_dividends(
                    {"date": "2024-06-15"},
                    {"date": "2024-12-15"},
                ),
            }
        },
    )

    update_dividend(etf.ef_id)

    events = EtfEvent.objects.filter(ee_etf=etf).order_by("ee_ex_date")
    assert events[0].ee_ex_date == date(2024, 12, 15)
    assert events[1].ee_ex_date == date(2025, 3, 15)


def test_real_payment_date(mock_requests, etf):
    mock_requests(
        "mytools.tasks.update_etf_dividend",
        responses={
            "finance.yahoo.com": {
                "json": yahoo_dividends(
                    {"date": "2024-12-15", "payDate": "2024-12-20"},
                ),
            }
        },
    )

    update_dividend(etf.ef_id)

    events = EtfEvent.objects.filter(ee_etf=etf).order_by("ee_ex_date")
    assert events[0].ee_payment_date == date(2024, 12, 20)
    assert events[0].ee_payment_estimated is False


def test_estimated_payment_date(mock_requests, etf):
    mock_requests(
        "mytools.tasks.update_etf_dividend",
        responses={
            "finance.yahoo.com": {
                "json": yahoo_dividends(
                    {"date": "2024-12-15"},
                ),
            }
        },
    )

    update_dividend(etf.ef_id)

    events = EtfEvent.objects.filter(ee_etf=etf).order_by("ee_ex_date")
    assert events[0].ee_payment_estimated is True
    assert events[0].ee_payment_date is not None
