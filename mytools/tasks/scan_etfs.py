from celery import shared_task

import requests

from datetime import timezone, datetime

from mytools.models import Etf
from .update_etf_dividend import update_dividend


def get_next_dividend(etf):
    today = datetime.now(timezone.utc).now().date()

    return (
        etf.events.filter(ee_ex_date__gt=today, ee_ex_estimated=False)
        .order_by("ee_ex_date")
        .first()
    )


@shared_task
def scan_etfs():
    today = datetime.now(timezone.utc).now().date()
    etfs = Etf.objects.filter(ef_symbol__isnull=False)

    for etf in etfs:
        next_event = get_next_dividend(etf)

        # No future event → must refresh
        if not next_event:
            update_dividend.delay(etf.ef_id)
            continue

        # Ex-date is close → refresh more often
        days_to_ex = (next_event.ee_ex_date - today).days

        if days_to_ex < 30:
            update_dividend.delay(etf.ef_id)
