from typing import Optional
from celery import shared_task
from datetime import datetime, timedelta

from mytools.models import InverterDataPoint
from mytools.lib.foxcloud import FoxCloud


@shared_task
def fetch_inverter_history(device_sn: str, date: Optional[datetime.date] = None):

    if date is None:
        date = datetime.now() - timedelta(days=1)

    variables = [
        "generation",
        "feedin",
        "gridConsumption",
        "loads",
        "chargeEnergyToTal",
        "dischargeEnergyToTal",
    ]

    fields_map = {
        "gridConsumption": "idp_grid_import_kwh",
        "feedin": "idp_grid_export_kwh",
        "dischargeEnergyToTal": "idp_battery_discharge_kwh",
        "chargeEnergyToTal": "idp_battery_charge_kwh",
    }

    payload = {
        "sn": device_sn,
        "year": date.year,
        "month": date.month,
        "day": date.day,
        "dimension": "day",
        "variables": variables,
    }

    api_response = FoxCloud().call_fox_api("/op/v0/device/report/query", payload)
    result_payload = api_response.get("result", None)

    if not result_payload:
        return

    record = InverterDataPoint(idp_date=date)
    batt_charge = 0
    batt_discharge = 0
    raw_gen = 0
    raw_loads = 0

    for variable_entry in result_payload:
        var_name = variable_entry.get("variable")
        field_name = fields_map.get(var_name)
        total = round(sum(variable_entry.get("values", [])), 2)

        if var_name == "generation":
            raw_gen = total
        elif var_name == "chargeEnergyToTal":
            batt_charge = total
        elif var_name == "dischargeEnergyToTal":
            batt_discharge = total
        elif var_name == "loads":
            raw_loads = total

        if field_name:
            setattr(record, field_name, total)

    true_pv_production = raw_gen + batt_charge
    true_home_consumption = raw_loads + batt_discharge
    record.idp_home_consumption_kwh = true_home_consumption
    record.idp_solar_generation_kwh = true_pv_production
    record.save()


@shared_task
def backfill_history_day_by_day(
    device_sn: str, start_date: str, end_date: Optional[str] = None
):

    if end_date is not None:
        _end_date = datetime.strptime(end_date, "%Y-%m-%d")
    else:
        _end_date = datetime.today()

    try:
        last_import = InverterDataPoint.objects.latest("idp_date")
        current_date = last_import.date + timedelta(days=1)
    except InverterDataPoint.DoesNotExist:
        current_date = datetime.strptime(start_date, "%Y-%m-%d")

    while current_date <= _end_date:
        fetch_inverter_history(device_sn, current_date)
        current_date += timedelta(days=1)
