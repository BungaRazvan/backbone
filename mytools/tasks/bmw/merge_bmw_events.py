from typing import List, Optional

from datetime import timedelta
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from django.db import transaction
from celery import shared_task

from mytools.models import Vehicle, BMWCarDataEvent, VehicleSession

NON_DRIVE_GAP = timedelta(minutes=5)
POST_SHUTDOWN_GRACE = timedelta(minutes=2)

MILES_TO_KM = Decimal("1.609344")
UK_GAL_TO_LITERS = Decimal("4.54609")
US_GAL_TO_LITERS = Decimal("3.78541")

# Exact descriptors from your CarData container
DESC_IGNITION = "vehicle.drivetrain.engine.isignitionon"
DESC_ENGINE_ACTIVE = "vehicle.drivetrain.engine.isactive"
DESC_IS_MOVING = "vehicle.ismoving"

DESC_ODOMETER = "vehicle.vehicle.travelleddistance"
DESC_END_ODOMETER = "vehicle.trip.segment.end.travelleddistance"
DESC_END_TIME = "vehicle.trip.segment.end.time"
DESC_END_HV_SOC = "vehicle.trip.segment.end.drivetrain.batterymanagement.hvsoc"
DESC_LIVE_HV_SOC = "vehicle.powertrain.electric.battery.stateofcharge.displayed"

DESC_EV_FRACTION = "vehicle.trip.segment.accumulated.drivetrain.transmission.setting.fractiondriveelectric"
DESC_RECUP_TOTAL = (
    "vehicle.trip.segment.accumulated.drivetrain.electricengine.recuperationtotal"
)
DESC_EV_ENERGY_COMFORT = "vehicle.trip.segment.accumulated.drivetrain.electricengine.energyconsumptioncomfort"
DESC_BATTERY_MAX_ENERGY = "vehicle.drivetrain.batterymanagement.maxenergy"

DESC_REMAINING_FUEL = "vehicle.drivetrain.fuelsystem.remainingfuel"
DESC_ENGINE_ECT = "vehicle.drivetrain.internalcombustionengine.engine.ect"
DESC_CHARGING_STATUS = "vehicle.drivetrain.electricengine.charging.status"
DESC_PORT_STATUS = "vehicle.body.chargingport.status"

DESC_LAT = "vehicle.cabin.infotainment.navigation.currentlocation.latitude"
DESC_LON = "vehicle.cabin.infotainment.navigation.currentlocation.longitude"

SUMMARY_DESCRIPTORS = {
    DESC_END_TIME,
    DESC_END_ODOMETER,
    DESC_END_HV_SOC,
    DESC_EV_FRACTION,
    DESC_RECUP_TOTAL,
    DESC_EV_ENERGY_COMFORT,
}

TRUE_VALUES = {"true", "1", "on", "active", "running", "yes"}
FALSE_VALUES = {"false", "0", "off", "inactive", "stopped", "no"}


SUMMARY_KEYS = {
    "timeofmostrecentdrive",
    "electricallydrivendistance",
    "electricalenergyconsumption",
    "fuelconsumption",
    "mileageafterlastdrive",
}


def _unwrap_event(ev: BMWCarDataEvent) -> tuple[object, str]:
    """Unwraps bridge payload {'data': {'<descriptor>': {'value': X, 'unit': Y}}} or flat {'value': X}."""

    payload = ev.payload

    if not isinstance(payload, dict):
        return payload, ""

    data_block = payload.get("data")

    if isinstance(data_block, dict) and ev.event_type in data_block:
        entry = data_block[ev.event_type]

        if isinstance(entry, dict):
            return entry.get("value"), str(entry.get("unit", "")).strip().lower()
        return entry, ""

    return payload.get("value", payload), str(payload.get("unit", "")).strip().lower()


def _to_decimal(val) -> Decimal | None:
    if val is None or isinstance(val, bool):
        return None
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _to_km(num: Decimal | None, unit: str) -> Decimal | None:
    if num is None:
        return None

    if unit in {"mi", "mls", "mile", "miles"}:
        return (num * MILES_TO_KM).quantize(Decimal("0.01"))

    if unit == "m":
        return (num / Decimal("1000")).quantize(Decimal("0.01"))

    return num


def _to_liters(num: Decimal | None, unit: str) -> Decimal | None:
    if num is None:
        return None

    if unit in {"gal_uk", "imp_gal"}:
        return (num * UK_GAL_TO_LITERS).quantize(Decimal("0.01"))

    if unit in {"gal", "gal_us"}:
        return (num * US_GAL_TO_LITERS).quantize(Decimal("0.01"))

    return num


def _extract_value(payload):
    if isinstance(payload, dict):
        return payload.get("value", payload)

    return payload


def _is_drive_start(key_lower: str, val_str: str) -> bool:
    return (
        key_lower in {DESC_IGNITION, DESC_ENGINE_ACTIVE, DESC_IS_MOVING}
        and val_str in TRUE_VALUES
    )


def _is_ignition_off(key_lower: str, val_str: str) -> bool:
    return key_lower == DESC_IGNITION and val_str in FALSE_VALUES


def _is_summary_event(key_lower):
    return key_lower in SUMMARY_DESCRIPTORS


@shared_task
def merge_bmw_events():
    now = timezone.now()

    for vehicle in Vehicle.objects.filter(is_active=True, make="BMW"):
        events = list(
            BMWCarDataEvent.objects.filter(vehicle=vehicle, processed=False).order_by(
                "timestamp", "received_at"
            )
        )

        if not events:
            continue

        process_vehicle_stream(vehicle, events, now)


def process_vehicle_stream(
    vehicle: Vehicle, events: List[BMWCarDataEvent], now: timezone.datetime
):

    buffer: List[BMWCarDataEvent] = []
    in_drive = False
    ignition_off_at = None
    saw_summary = False

    def flush(activity_override: Optional[str] = None):
        nonlocal buffer, in_drive, ignition_off_at, saw_summary

        if buffer:
            save_session(vehicle, buffer, activity_override=activity_override)

        buffer = []
        in_drive = False
        ignition_off_at = None
        saw_summary = False

    for ev in events:
        ev_time = ev.event_time
        key_lower = (ev.event_type or "").lower()
        raw_val = _extract_value(ev.payload)
        val_str = str(raw_val).strip().lower()

        if not buffer:
            buffer.append(ev)

            if _is_drive_start(key_lower, val_str):
                in_drive = True
            elif _is_summary_event(key_lower):
                saw_summary = True
                in_drive = True

            continue

        prev_time = buffer[-1].event_time

        # --- CASE 1: Currently inside a DRIVE cycle ---
        if in_drive:
            if ignition_off_at and _is_drive_start(key_lower, val_str):
                flush(VehicleSession.ActivityType.DRIVE)
                buffer.append(ev)
                in_drive = True
                continue

            if (
                ignition_off_at
                and (ev_time - ignition_off_at) > POST_SHUTDOWN_GRACE
                and not _is_summary_event(key_lower)
            ):
                flush(VehicleSession.ActivityType.DRIVE)
                buffer.append(ev)

                if _is_drive_start(key_lower, val_str):
                    in_drive = True

                continue

        if not in_drive:
            if _is_drive_start(key_lower, val_str):
                flush()
                buffer.append(ev)
                in_drive = True
                continue

            if (ev_time - prev_time) > NON_DRIVE_GAP:
                flush()
                buffer.append(ev)

                if _is_summary_event(key_lower):
                    in_drive = True
                    saw_summary = True

                continue

        buffer.append(ev)

        if _is_ignition_off(key_lower, val_str) and ignition_off_at is None:
            ignition_off_at = ev_time
        elif _is_summary_event(key_lower):
            saw_summary = True

            if not in_drive:
                in_drive = True

    if not buffer:
        return

    quiet_for = now - buffer[-1].event_time

    if in_drive:
        if ignition_off_at and (saw_summary or quiet_for >= POST_SHUTDOWN_GRACE):
            flush(VehicleSession.ActivityType.DRIVE)

    else:
        if quiet_for >= NON_DRIVE_GAP:
            flush()


@transaction.atomic
def save_session(
    vehicle: Vehicle,
    cluster: List[BMWCarDataEvent],
    activity_override: VehicleSession.ActivityType,
):
    merged_state = {}
    route_points = []
    keys_seen = set()

    odometers = []
    hv_socs = []
    fuels_liters = []
    ect_temps = []

    end_segment_odo = None
    end_segment_soc = None
    ev_fraction_pct = None
    recup_rate = None
    ev_kwh_comfort = None
    usable_battery_kwh = None
    activity = None

    recup_unit = ""

    is_charging = False

    for ev in cluster:
        key = ev.event_type or ""
        key_lower = key.lower()
        keys_seen.add(key_lower)

        val, unit = _unwrap_event(ev)
        merged_state[key] = {"value": val, "unit": unit} if unit else val
        num = _to_decimal(val)
        val_upper = str(val).strip().upper()

        if key_lower == DESC_ODOMETER and num is not None:
            odometers.append(_to_km(num, unit))

        elif key_lower == DESC_END_ODOMETER and num is not None:
            end_segment_odo = _to_km(num, unit)

        elif key_lower == DESC_LIVE_HV_SOC and num is not None:
            hv_socs.append(num)

        elif key_lower == DESC_END_HV_SOC and num is not None:
            end_segment_soc = num

        elif key_lower == DESC_REMAINING_FUEL and num is not None:
            fuels_liters.append(num)

        elif key_lower == DESC_ENGINE_ECT and num is not None:
            ect_temps.append(num)

        elif key_lower == DESC_EV_FRACTION and num is not None:
            ev_fraction_pct = num

        elif key_lower == DESC_RECUP_TOTAL and num is not None:
            recup_rate = num
            recup_unit = unit

        elif key_lower == DESC_EV_ENERGY_COMFORT and num is not None:
            ev_kwh_confort = num

        elif key_lower == DESC_BATTERY_MAX_ENERGY and num is not None:
            usable_battery_kwh = num

        if (
            key_lower == DESC_CHARGING_STATUS
            and val_upper == "CHARGINGACTIVE"
            or key_lower == DESC_PORT_STATUS
            and val_upper == "CONNECTED"
        ):
            is_charging = True

        if key_lower in {DESC_LAT, DESC_LON, DESC_LIVE_HV_SOC}:
            route_points.append(
                {
                    "ts": ev.event_time,
                    "key": key,
                    "value": val,
                    "unit": unit,
                }
            )

    # Classify session
    if activity_override:
        activity = activity_override

    elif keys_seen & SUMMARY_DESCRIPTORS:
        activity = VehicleSession.ActivityType.DRIVE

    elif is_charging:
        activity = VehicleSession.ActivityType.CHARGE

    elif any("door" in k or "trunk" in k or "alarm" in k for k in keys_seen):
        activity = VehicleSession.ActivityType.ACCESS

    else:
        activity = VehicleSession.ActivityType.OTHER

    if end_segment_odo is not None:
        odometers.append(end_segment_odo)

    start_odo = min(odometers) if odometers else None
    end_odo = max(odometers) if odometers else None
    total_dist_km = (end_odo - start_odo) if odometers else None

    electrict_dist_km = None
    if total_dist_km is not None and ev_fraction_pct is not None:
        electrict_dist_km = (total_dist_km * ev_fraction_pct / Decimal("100")).quantize(
            Decimal("0.01")
        )

    start_soc = hv_socs[0] if hv_socs else None
    end_soc = (
        end_segment_soc
        if end_segment_soc is not None
        else (hv_socs[-1] if hv_socs else None)
    )

    # Net electric kWh consumed
    electric_kwh = ev_kwh_comfort
    if (
        electric_kwh is None
        and start_soc is not None
        and end_soc is not None
        and start_soc > end_soc
    ):
        pack_kwh = usable_battery_kwh or Decimal("10.4")
        electric_kwh = ((start_soc - end_soc) / Decimal("100") * pack_kwh).quantize(
            Decimal("0.01")
        )

    # Recuperated energy (kWh/100km or kWh/62mi)
    recuperated_kwh = None
    if recup_rate is not None and total_dist_km is not None:
        divisor = (
            Decimal("62") if recup_unit in {"kwh/62mi", "kwh/62 mi"} else Decimal("100")
        )
        recuperated_kwh = (recup_rate * total_dist_km / divisor).quantize(
            Decimal("0.01")
        )

    # Fuel delta & petrol engine detection
    fuel_liters = None
    if len(fuels_liters) >= 2 and fuels_liters[0] > fuels_liters[-1]:
        fuel_liters = (fuels_liters[0] - fuels_liters[-1]).quantize(Decimal("0.01"))

    ect_rise = (
        (max(ect_temps) - min(ect_temps)) if len(ect_temps) >= 2 else Decimal("0")
    )
    ice_engine_ran = bool((fuel_liters and fuel_liters > 0) or ect_rise > Decimal("5"))

    session = VehicleSession.objects.create(
        vehicle=vehicle,
        activity_type=activity,
        started_at=cluster[0].event_time,
        ended_at=cluster[-1].event_time,
        event_count=len(cluster),
        merged_state=merged_state,
        start_odometer_km=start_odo,
        end_odometer_km=end_odo,
        total_distance_km=total_dist_km,
        electric_distance_km=electrict_dist_km,
        fuel_consumed_liters=fuel_liters,
        electric_consumed_kwh=electric_kwh,
        recuperated_kwh=recuperated_kwh,
        ice_engine_ran=ice_engine_ran,
        start_soc=start_soc,
        end_soc=end_soc,
        route_points=(
            route_points if activity == VehicleSession.ActivityType.DRIVE else []
        ),
    )

    BMWCarDataEvent.objects.filter(id__in=[e.id for e in cluster]).update(
        processed=True,
        session=session,
    )
