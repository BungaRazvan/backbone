from typing import Optional
from celery import shared_task
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from mytools.models import InverterDataPoint

from .fetch import fetch_inverter_history_by_month


@shared_task
def backfill_historical_stats(
    device_sn: str,
    start_date_str: str,
    end_date_str: Optional[str] = None,
    tz: str = "Europe/London",
):
    """
    Triggers monthly batch chunks based on a custom date range.
    """

    _tz = ZoneInfo(tz)

    try:
        start_date = InverterDataPoint.objects.latest("idp_date").idp_date
    except InverterDataPoint.DoesNotExist:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()

    if end_date_str:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    else:
        end_date = datetime.now(_tz).date()

    current_date = start_date

    # Track which year-month pairs have already been dispatched to avoid duplicate work
    processed_months = set()

    while current_date <= end_date:
        month_key = (current_date.year, current_date.month)

        if month_key not in processed_months:
            print(
                f"Dispatching monthly fetch for: {current_date.year}-{current_date.month:02d}"
            )
            records = fetch_inverter_history_by_month(
                device_sn, current_date.year, current_date.month
            )

            if records:
                InverterDataPoint.objects.bulk_create(records)

            processed_months.add(month_key)

        # Advance the pointer safely past any month boundary issues
        # Moving forward 28 days guarantees landing into the next bracket or moving right along
        current_date += timedelta(days=20)
        # Fast forward past the month safely
        if current_date.month == month_key[1] and current_date.year == month_key[0]:
            current_date = current_date.replace(day=28) + timedelta(days=4)
