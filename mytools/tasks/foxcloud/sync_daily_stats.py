from datetime import datetime, timedelta


from celery import shared_task
from zoneinfo import ZoneInfo

from .fetch import fetch_inverter_history_by_month


@shared_task
def sync_daily_stats(
    device_sn: str,
    tz: str = "Europe/London",
):

    _tz = ZoneInfo(tz)
    today = datetime.now(_tz).date() - timedelta(days=1)

    records = fetch_inverter_history_by_month(device_sn, today.year, today.month)

    if not records:
        return

    for record in reversed(records):
        if record.idp_date == today:
            record.save()
            break
        else:
            continue
