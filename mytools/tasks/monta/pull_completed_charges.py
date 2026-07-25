from datetime import datetime, timedelta

from decimal import Decimal

from celery import shared_task

from mytools.lib.monta import Monta
from mytools.models import ChargePointHistory
import json


@shared_task
def pull_completed_charges():
    monta = Monta()
    params = {"state": "completed"}

    today_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        latest_record = ChargePointHistory.objects.latest("cph_completed_at")
        params["fromDate"] = latest_record.cph_completed_at.isoformat()
        params["toDate"] = today_str

    except ChargePointHistory.DoesNotExist:
        params["toDate"] = today_str

    models = []
    page = 1

    while True:
        resp = monta.get("charges", params=params).json()
        print(resp)
        meta = resp.get("meta")
        data = resp.get("data")
        total_page_count = meta.get("totalPageCount") or 0
        print(json.dumps(data, indent=2))
        for entry in data:
            if entry.get("consumedKwh"):
                # Safely parse start and end meters to prevent scientific notation formatting glitches
                start_meter = entry.get("startMeterKwh")
                end_meter = entry.get("endMeterKwh")

                start_meter_kwh = (
                    Decimal(str(start_meter))
                    if start_meter is not None
                    else Decimal("0.0000")
                )
                end_meter_kwh = (
                    Decimal(str(end_meter))
                    if end_meter is not None
                    else Decimal("0.0000")
                )
                consumed_kwh = Decimal(str(entry.get("consumedKwh", "0")))

                models.append(
                    ChargePointHistory(
                        cph_kwh=consumed_kwh,
                        cph_start_meter_kwh=start_meter_kwh,
                        cph_end_meter_kwh=end_meter_kwh,
                        cph_started_at=entry.get("startedAt"),
                        cph_completed_at=entry.get("stoppedAt"),
                        cph_state=entry.get("state"),
                        cph_created_at=entry.get("createdAt"),
                    )
                )

        if len(models):
            ChargePointHistory.objects.bulk_create(models)

        if page >= total_page_count:
            break

        page += 1
