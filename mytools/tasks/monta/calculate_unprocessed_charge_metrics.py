import logging
import zoneinfo

from datetime import datetime, time, timedelta
from decimal import Decimal

from celery import shared_task
from django.db.models import Q

from mytools.models import ChargePointHistory, TariffPeriod
from mytools.lib.foxcloud import FoxCloud


def get_hourly_metrics_for_session(
    device_sn: str, cph: ChargePointHistory, timezone: str = "Europe/London"
) -> dict[str, Decimal]:
    tz = zoneinfo.ZoneInfo(timezone)

    local_start = cph.cph_started_at.astimezone(tz)
    local_end = cph.cph_completed_at.astimezone(tz)

    current_date = local_start.date()
    end_date = local_end.date()

    totals = {
        "loads": Decimal("0.0"),
        "gridConsumption": Decimal("0.0"),
        "dischargeEnergyToTal": Decimal("0.0"),
    }

    while current_date <= end_date:
        payload = {
            "sn": device_sn,
            "year": current_date.year,
            "month": current_date.month,
            "day": current_date.day,
            "dimension": "day",
            "variables": ["loads", "gridConsumption", "dischargeEnergyToTal"],
        }

        api_response = FoxCloud().call_fox_api("/op/v0/device/report/query", payload)
        results = api_response.get("result", [])

        # Map variable name -> 24-element hourly list
        variable_maps = {
            "loads": [0.0] * 24,
            "gridConsumption": [0.0] * 24,
            "dischargeEnergyToTal": [0.0] * 24,
        }

        for item in results:
            var_name = item.get("variable")
            # Fox Cloud returns a list of 24 floats under 'values'
            values_list = item.get("values", [])

            if var_name in variable_maps and isinstance(values_list, list):
                variable_maps[var_name] = values_list

        # Daily start and end bounds in local time
        day_start_dt = (
            local_start
            if current_date == local_start.date()
            else datetime.combine(current_date, time(0, 0, 0), tzinfo=tz)
        )
        day_end_dt = (
            local_end
            if current_date == local_end.date()
            else datetime.combine(current_date, time(23, 59, 59, 999999), tzinfo=tz)
        )

        # Loop through hour indices 0..23
        for hour_idx in range(24):
            slot_start = datetime.combine(current_date, time(hour_idx, 0, 0), tzinfo=tz)
            slot_end = datetime.combine(
                current_date,
                (
                    time(hour_idx, 59, 59, 999999)
                    if hour_idx < 23
                    else time(23, 59, 59, 999999)
                ),
                tzinfo=tz,
            )

            # Skip hour if outside charging window
            if day_end_dt < slot_start or day_start_dt > slot_end:
                continue

            overlap_start = max(day_start_dt, slot_start)
            overlap_end = min(day_end_dt, slot_end)
            overlap_seconds = max(0.0, (overlap_end - overlap_start).total_seconds())

            fraction = min(1.0, overlap_seconds / 3600.0)

            for key in totals:
                raw_kwh_list = variable_maps[key]
                if hour_idx < len(raw_kwh_list):
                    raw_kwh = raw_kwh_list[hour_idx] or 0.0
                    totals[key] += Decimal(str(raw_kwh * fraction))

        current_date += timedelta(days=1)

    return {k: v.quantize(Decimal("0.0001")) for k, v in totals.items()}


def get_active_tariffs_for_date(
    target_date,
) -> tuple[TariffPeriod | None, Decimal, TariffPeriod | None, Decimal]:
    """Fetches the active Import and Export (SEG) tariffs for a specific local date."""

    import_tariff = (
        TariffPeriod.objects.filter(
            tp_start_date__lte=target_date,
            tp_standard_import_rate__gt=0,
        )
        .filter(
            Q(tp_end_date__gte=target_date) | Q(tp_end_date__isnull=True),
        )
        .order_by("-tp_start_date")
        .first()
    )

    export_tariff = (
        TariffPeriod.objects.filter(
            tp_start_date__lte=target_date,
            tp_standard_export_rate__gt=0,
        )
        .filter(
            Q(tp_end_date__gte=target_date) | Q(tp_end_date__isnull=True),
        )
        .order_by("-tp_start_date")
        .first()
    )

    import_rate = (
        Decimal(str(import_tariff.tp_standard_import_rate))
        if import_tariff
        else Decimal("0.3000")
    )
    export_rate = (
        Decimal(str(export_tariff.tp_standard_export_rate))
        if export_tariff
        else Decimal("0.0500")
    )

    return import_tariff, import_rate, export_tariff, export_rate


def calculate_charge_stats(
    device_sn: str, cph: ChargePointHistory, timezone: str = "Europe/London"
):
    """Calculates solar/grid kWh split and costs for a ChargePointHistory session

    using hourly Fox Cloud inverter metrics.
    """

    # 1. Fetch hourly inverter totals during the session
    metrics = get_hourly_metrics_for_session(
        device_sn=device_sn, cph=cph, timezone=timezone
    )

    total_loads = metrics["loads"]
    grid_import = metrics["gridConsumption"]
    battery_discharge = metrics["dischargeEnergyToTal"]
    total_ev_kwh = cph.cph_kwh

    # 2. Derive Direct Solar generation consumed during window
    # Self-generated/stored power = Total Loads minus what came from the Grid
    self_generated_kwh = max(Decimal("0.0"), total_loads - grid_import)

    # Calculate ratio of free energy vs grid import for the house during this hour
    if total_loads > Decimal("0.0"):
        green_ratio = min(Decimal("1.0"), self_generated_kwh / total_loads)
    else:
        green_ratio = Decimal("0.0")

    # 4. Split EV session kWh based on calculated ratio
    cph_solar_kwh = (total_ev_kwh * green_ratio).quantize(Decimal("0.0001"))
    cph_grid_kwh = total_ev_kwh - cph_solar_kwh

    # 5. Fetch Tariffs
    import_tariff, GRID_RATE, export_tariff, FEED_IN_RATE = get_active_tariffs_for_date(
        cph.cph_started_at.date()
    )
    # 6. Cost Calculations
    cph_gross_cost = (total_ev_kwh * GRID_RATE).quantize(Decimal("0.00000008"))
    cph_net_cost = ((cph_grid_kwh * GRID_RATE)).quantize(Decimal("0.0001"))
    cph.cph_feed_in_loss = (cph_solar_kwh * FEED_IN_RATE).quantize(Decimal("0.0001"))

    # 7. Persist to Model
    cph.cph_solar_kwh = cph_solar_kwh
    cph.cph_grid_kwh = cph_grid_kwh
    cph.cph_gross_cost = cph_gross_cost
    cph.cph_net_cost = cph_net_cost
    cph.cph_import_tariff = import_tariff
    cph.cph_export_tariff = export_tariff
    cph.cph_battery_kwh = battery_discharge
    cph.save()


@shared_task
def calculate_unprocessed_charge_metrics(
    device_sn: str, timezone: str = "Europe/London"
):
    charges = ChargePointHistory.objects.filter(cph_gross_cost__isnull=True)

    for charge in charges:
        calculate_charge_stats(device_sn, charge, timezone)
