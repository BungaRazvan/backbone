from typing import Optional

from celery import shared_task

from mytools.models import Electricity, Seg, InverterDataPoint
from datetime import date, timedelta


@shared_task
def calculate_yearly_electric_usage(year: Optional[int] = None):

    if year is None:
        year = date.today().year
