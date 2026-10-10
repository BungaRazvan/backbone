import hashlib

import pytest
from datetime import datetime
from decimal import Decimal

from freezegun import freeze_time

from mytools.lib.foxcloud import FoxCloud
from mytools.tasks.foxcloud.fetch import fetch_inverter_history_by_month
from mytools.tasks.monta.pull_completed_charges import pull_completed_charges
from mytools.tasks.monta.calculate_unprocessed_charge_metrics import (
    calculate_unprocessed_charge_metrics,
)
from mytools.models import ChargePointHistory


@pytest.fixture
def celery_includes():
    return [
        "mytools.tasks.foxcloud.fetch",
        "mytools.tasks.monta.pull_completed_charges",
        "mytools.tasks.monta.calculate_unprocessed_charge_metrics",
    ]


@freeze_time("2026-10-02 20:03:59")
def test_foxcloud_signature_uses_crlf_separators():
    fox_cloud = FoxCloud()
    path = "/op/v0/device/report/query"

    signature, timestamp = fox_cloud.get_signature(path)
    expected = hashlib.md5(
        rf"{path}\r\n{fox_cloud.token}\r\n{timestamp}".encode("UTF-8")
    ).hexdigest()

    assert signature == expected


def test_call_fox_api_raises_on_api_error(monkeypatch):
    class ApiErrorResponse:
        status_code = 200
        headers = {}

        def raise_for_status(self):
            pass

        def json(self):
            return {"errno": 40256, "msg": "illegal signature"}

    requested_urls = []

    def mock_post(url, **kwargs):
        requested_urls.append(url)
        return ApiErrorResponse()

    monkeypatch.setattr("mytools.lib.foxcloud.requests.post", mock_post)

    with pytest.raises(RuntimeError, match="FoxESS API error 40256"):
        FoxCloud().call_fox_api("/op/v0/device/list", {})

    assert requested_urls == ["https://www.foxesscloud.com/op/v0/device/list"]


def test_fetch_inverter_history_by_month_handles_foxcloud_api_response(
    db,
    mock_requests,
):
    mock_requests(
        "mytools.lib.foxcloud",
        responses={
            "foxesscloud.com/op/v0/device/report/query": {
                "json": {
                    "result": [
                        {
                            "variable": "gridConsumption",
                            "values": [1.0, 2.0, 3.0],
                        },
                        {
                            "variable": "feedin",
                            "values": [0.5, 0.0, 0.0],
                        },
                        {
                            "variable": "dischargeEnergyToTal",
                            "values": [0.2, 0.0, 0.0],
                        },
                        {
                            "variable": "chargeEnergyToTal",
                            "values": [0.1, 0.0, 0.0],
                        },
                        {
                            "variable": "PVEnergyTotal",
                            "values": [0.4, 0.0, 0.0],
                        },
                        {
                            "variable": "loads",
                            "values": [2.0, 0.0, 0.0],
                        },
                    ]
                }
            }
        },
    )

    records = fetch_inverter_history_by_month("SN123", 2026, 6)

    assert len(records) == 3
    assert records[0].idp_date == datetime(2026, 6, 1).date()
    assert records[0].idp_grid_import_kwh == Decimal("1.00")
    assert records[0].idp_grid_export_kwh == Decimal("0.50")
    assert records[0].idp_battery_discharge_kwh == Decimal("0.20")
    assert records[0].idp_battery_charge_kwh == Decimal("0.10")
    assert records[0].idp_solar_generation_kwh == Decimal("0.40")
    assert records[0].idp_home_consumption_kwh == Decimal("2.61")


def test_pull_completed_charges_saves_charge_point_history(db, mock_requests):
    mock_requests(
        "mytools.lib.monta",
        responses={
            "public-api.monta.com/api/v1/charges": {
                "json": {
                    "meta": {"totalPageCount": 1},
                    "data": [
                        {
                            "consumedKwh": 10.5,
                            "startMeterKwh": 1234.56,
                            "endMeterKwh": 1245.06,
                            "startedAt": "2026-06-01T10:00:00Z",
                            "stoppedAt": "2026-06-01T11:00:00Z",
                            "createdAt": "2026-06-01T11:05:00Z",
                            "state": "completed",
                        }
                    ],
                }
            },
            "https://public-api.monta.com/api/v1/auth/token": {
                "json": {
                    "accessToken": "fake-token",
                    "accessTokenExpirationDate": "2026-07-01T00:00:00Z",
                }
            },
        },
    )

    pull_completed_charges()

    assert ChargePointHistory.objects.count() == 1
    record = ChargePointHistory.objects.first()
    assert record.cph_kwh == Decimal("10.5")
    assert record.cph_start_meter_kwh == Decimal("1234.56")
    assert record.cph_end_meter_kwh == Decimal("1245.06")
    assert record.cph_state == "completed"


@freeze_time("2026-06-02")
def test_calculate_unprocessed_charge_metrics_updates_charge_point_history(
    db,
    mock_requests,
):
    record = ChargePointHistory.objects.create(
        cph_kwh=Decimal("20.0"),
        cph_start_meter_kwh=Decimal("1000.0"),
        cph_end_meter_kwh=Decimal("1020.0"),
        cph_started_at=datetime(2026, 6, 1, 10, 0, 0),
        cph_completed_at=datetime(2026, 6, 1, 11, 0, 0),
        cph_created_at=datetime(2026, 6, 1, 11, 5, 0),
        cph_state="completed",
    )

    mock_requests(
        "mytools.lib.foxcloud",
        responses={
            "foxesscloud.com/op/v0/device/report/query": {
                "json": {
                    "result": [
                        {
                            "variable": "loads",
                            "values": [2.0] * 24,
                        },
                        {
                            "variable": "gridConsumption",
                            "values": [1.0] * 24,
                        },
                        {
                            "variable": "dischargeEnergyToTal",
                            "values": [0.5] * 24,
                        },
                    ]
                }
            }
        },
    )

    calculate_unprocessed_charge_metrics("SN123")

    record.refresh_from_db()
    assert record.cph_solar_kwh > 0
    assert record.cph_grid_kwh > 0
    assert record.cph_gross_cost is not None
    assert record.cph_net_cost is not None
