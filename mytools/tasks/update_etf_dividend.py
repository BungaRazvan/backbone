import requests

from datetime import datetime, timedelta, timezone
from celery import shared_task

from mytools.models import Etf, EtfEvent


@shared_task
def update_etf_dividend(etf_id: int) -> None:

    etf = Etf.objects.get(pk=etf_id)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{etf.ef_symbol}?range=2y&interval=1d&events=div"

    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    data = response.json()
    events = (
        data.get("chart", {})
        .get("result", [{}])[0]
        .get("events", {})
        .get("dividends", {})
    )

    today = datetime.now(timezone.utc).date()

    for div in events.values():
        ex_ts = div.get("date")

        if not ex_ts:
            continue

        ex_date = datetime.fromtimestamp(ex_ts).date()

        if ex_date <= today:
            continue

        pay_ts = div.get("payDate")

        if pay_ts:
            payment_date = datetime.fromtimestamp(pay_ts).date()
            payment_estimated = False
        else:
            payment_date = ex_date + timedelta(days=etf.ef_pay_lag_days)
            payment_estimated = True

        EtfEvent.objects.update_or_create(
            ee_etf=etf,
            ee_ex_date=ex_date,
            defaults={
                "ee_pay_per_share": etf.to_upper_unit(div.get("amount", 0)),
                "ee_payment_date": payment_date,
                "ee_payment_estimated": payment_estimated,
            },
        )
