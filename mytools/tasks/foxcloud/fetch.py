from datetime import date

from celery import shared_task

from mytools.lib.foxcloud import FoxCloud

from mytools.models import InverterDataPoint


@shared_task
def fetch_inverter_history_by_month(
    device_sn: str, target_year: int, target_month: int
):
    """
    Fetches historical stats for an entire month at once using "dimension": "month".
    This bypasses the hourly-bucket rounding bugs of the Fox API and perfectly
    matches the official app data for every single day of that month.
    """

    variables = [
        "feedin",
        "gridConsumption",
        "loads",
        "chargeEnergyToTal",
        "dischargeEnergyToTal",
        "PVEnergyTotal",
    ]

    fields_map = {
        "gridConsumption": "idp_grid_import_kwh",
        "feedin": "idp_grid_export_kwh",
        "dischargeEnergyToTal": "idp_battery_discharge_kwh",
        "chargeEnergyToTal": "idp_battery_charge_kwh",
        "PVEnergyTotal": "idp_solar_generation_kwh",
        "loads": "idp_home_consumption_kwh",
    }

    payload = {
        "sn": device_sn,
        "year": target_year,
        "month": target_month,
        "dimension": "month",
        "variables": variables,
    }

    api_response = FoxCloud().call_fox_api("/op/v0/device/report/query", payload)
    result_payload = api_response.get("result", None)

    if not result_payload:
        print(f"No data returned for {target_year}-{target_month:02d}")
        return

    # Structure to hold daily metrics: {day_num: {field_name: value}}
    # e.g., {1: {"idp_solar_generation_kwh": 12.4, ...}}
    monthly_data = {}

    for variable_entry in result_payload:
        var_name = variable_entry.get("variable")
        field_name = fields_map.get(var_name)

        if not field_name:
            continue

        # 'values' contains an item for each day of the month (index 0 = Day 1)
        daily_values = variable_entry.get("values", [])

        for index, value in enumerate(daily_values):
            day_num = index + 1
            if day_num not in monthly_data:
                monthly_data[day_num] = {}

            monthly_data[day_num][field_name] = round(value, 2)

        if not daily_values:
            monthly_data[day_num][field_name] = 0

    records = []
    for day_num, fields in monthly_data.items():
        try:
            # Safely build the exact calendar date
            record_date = date(target_year, target_month, day_num)
        except ValueError:
            continue

        record = InverterDataPoint(idp_date=record_date)

        for field_name, total_value in fields.items():
            setattr(record, field_name, total_value)

        raw_loads = fields.get("idp_home_consumption_kwh", 0.0)
        batt_discharge = fields.get("idp_battery_discharge_kwh", 0.0)

        if raw_loads > 0:
            # 5% battery conversion overhead + ~0.6 kWh flat daily inverter standing load
            adjusted_home_consumption = round(
                raw_loads + (batt_discharge * 0.05) + 0.6, 2
            )
            record.idp_home_consumption_kwh = adjusted_home_consumption
        else:
            record.idp_home_consumption_kwh = 0.0

        records.append(record)

    return records
