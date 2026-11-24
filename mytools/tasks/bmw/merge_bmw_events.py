import json
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from itertools import groupby
from typing import List, Optional

from celery import shared_task
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.utils import timezone

from mytools.models import BMWCarDataEvent, Vehicle, VehicleSession

NON_DRIVE_GAP = timedelta(minutes=5)
POST_SHUTDOWN_GRACE = timedelta(minutes=2)
DRIVE_IDLE_TIMEOUT = timedelta(minutes=15)
CHARGE_IDLE_TIMEOUT = timedelta(hours=3)

MILES_TO_KM = Decimal("1.609344")
UK_GAL_TO_LITERS = Decimal("4.54609")
US_GAL_TO_LITERS = Decimal("3.78541")

# Exact descriptors from your CarData container
DESC_IGNITION = "vehicle.drivetrain.engine.isignitionon"
DESC_ENGINE_ACTIVE = "vehicle.drivetrain.engine.isactive"
DESC_IS_MOVING = "vehicle.ismoving"
DESC_DOOR_STATUS = "vehicle.cabin.door.status"

DESC_ODOMETER = "vehicle.vehicle.travelleddistance"
DESC_END_ODOMETER = "vehicle.trip.segment.end.travelleddistance"
DESC_END_TIME = "vehicle.trip.segment.end.time"
DESC_END_HV_SOC = "vehicle.trip.segment.end.drivetrain.batterymanagement.hvsoc"
DESC_LIVE_HV_SOC = "vehicle.powertrain.electric.battery.stateofcharge.displayed"
DESC_KOMBI_ELEC_RANGE = "vehicle.drivetrain.electricengine.kombiremainingelectricrange"
DESC_EV_FRACTION = "vehicle.trip.segment.accumulated.drivetrain.transmission.setting.fractiondriveelectric"
DESC_RECUP_TOTAL = (
    "vehicle.trip.segment.accumulated.drivetrain.electricengine.recuperationtotal"
)
DESC_EV_ENERGY_COMFORT = "vehicle.trip.segment.accumulated.drivetrain.electricengine.energyconsumptioncomfort"
DESC_AVG_ELEC_CONSUMPTION = "vehicle.drivetrain.avgelectricrangeconsumption"
SOC_BOUNDARY_WINDOW = timedelta(minutes=15)
DESC_SME_ENERGY_DELTA_FULL = (
    "vehicle.drivetrain.electricengine.charging.smeenergydeltafullycharged"
)
DESC_BATTERY_MAX_ENERGY = "vehicle.drivetrain.batterymanagement.maxenergy"

DESC_REMAINING_FUEL = "vehicle.drivetrain.fuelsystem.remainingfuel"
DESC_ENGINE_ECT = "vehicle.drivetrain.internalcombustionengine.engine.ect"
DESC_CHARGING_STATUS = "vehicle.drivetrain.electricengine.charging.status"
DESC_PORT_STATUS = "vehicle.body.chargingport.status"

DESC_LAT = "vehicle.cabin.infotainment.navigation.currentlocation.latitude"
DESC_LON = "vehicle.cabin.infotainment.navigation.currentlocation.longitude"
DESC_ALTITUDE = "vehicle.cabin.infotainment.navigation.currentlocation.altitude"

SUMMARY_DESCRIPTORS = {
    DESC_END_TIME,
    DESC_END_ODOMETER,
    DESC_END_HV_SOC,
}

TRUE_VALUES = {"true", "1", "on", "active", "running", "yes"}
FALSE_VALUES = {"false", "0", "off", "inactive", "stopped", "no"}

ACTIVE_CHARGE_STATUSES = {
    "CHARGINGACTIVE",
    "INITIALIZATION",
    "CHARGINGPAUSED",
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


def _to_meters(num: Decimal | None, unit: str) -> Decimal | None:
    if num is None:
        return None

    if unit in {"", "m", "meter", "meters"}:
        return num
    if unit in {"km", "kilometer", "kilometers"}:
        return num * Decimal("1000")
    if unit in {"ft", "foot", "feet"}:
        return num * Decimal("0.3048")

    return None


def _build_route_points(route_samples: List[dict]) -> List[dict]:
    current_lat = None
    current_lon = None
    signals = {}
    points = []
    ordered_samples = sorted(route_samples, key=lambda sample: sample.get("ts") or "")

    for ts, samples in groupby(ordered_samples, key=lambda sample: sample.get("ts")):
        coordinates_changed = False
        altitude_updated = False

        for sample in samples:
            key = (sample.get("key") or "").lower()
            value = sample.get("value")
            unit = sample.get("unit", "")

            if key in {DESC_LAT, DESC_LON}:
                num = _to_decimal(value)
                if num is None:
                    continue
                if key == DESC_LAT:
                    current_lat = float(num)
                else:
                    current_lon = float(num)
                coordinates_changed = True
            elif key == DESC_ALTITUDE:
                altitude_m = _to_meters(_to_decimal(value), unit)
                if altitude_m is not None:
                    signals["altitude_m"] = {
                        "value": float(altitude_m),
                        "unit": "m",
                        "ts": ts,
                    }
                    altitude_updated = True
            elif key == DESC_LIVE_HV_SOC:
                num = _to_decimal(value)
                if num is not None:
                    signals["soc"] = {
                        "value": float(num),
                        "unit": unit,
                        "ts": ts,
                    }
            elif key == DESC_ENGINE_ACTIVE:
                normalized = str(value).strip().lower()
                if isinstance(value, bool):
                    engine_active = value
                elif normalized in TRUE_VALUES:
                    engine_active = True
                elif normalized in FALSE_VALUES:
                    engine_active = False
                else:
                    continue
                signals["engine_active"] = {
                    "value": engine_active,
                    "unit": unit,
                    "ts": ts,
                }
            elif key == DESC_KOMBI_ELEC_RANGE:
                range_km = _to_km(_to_decimal(value), unit)
                if range_km is not None:
                    signals["electric_range_km"] = {
                        "value": float(range_km),
                        "unit": "km",
                        "ts": ts,
                    }

        if coordinates_changed and current_lat is not None and current_lon is not None:
            points.append(
                {
                    "ts": ts,
                    "lat": current_lat,
                    "lon": current_lon,
                    "signals": {name: dict(signal) for name, signal in signals.items()},
                }
            )
        elif not coordinates_changed and points and altitude_updated:
            points[-1]["signals"]["altitude_m"] = dict(signals["altitude_m"])

    return points


def _to_liters(num: Decimal | None, unit: str) -> Decimal | None:
    if num is None:
        return None

    if unit in {"gal_uk", "imp_gal"}:
        return (num * UK_GAL_TO_LITERS).quantize(Decimal("0.01"))

    if unit in {"gal", "gal_us"}:
        return (num * US_GAL_TO_LITERS).quantize(Decimal("0.01"))

    return num


def _is_drive_start(key_lower: str, val_str: str) -> bool:
    return (
        key_lower in {DESC_IGNITION, DESC_ENGINE_ACTIVE, DESC_IS_MOVING}
        and val_str in TRUE_VALUES
    )


def _is_ignition_off(key_lower: str, val_str: str) -> bool:
    return key_lower == DESC_IGNITION and val_str in FALSE_VALUES


def _is_summary_event(key_lower: str) -> bool:
    return key_lower in SUMMARY_DESCRIPTORS


def _lock_state(key_lower: str, val_str: str) -> Optional[str]:
    if key_lower != DESC_DOOR_STATUS:
        return None

    if val_str == "unlocked":
        return "UNLOCK"

    if val_str in {"locked", "secured"}:
        return "LOCK"

    return None


@shared_task(ignore_result=True)
def merge_bmw_events():
    now = timezone.now()

    for vehicle in Vehicle.objects.filter(is_active=True, make="BMW"):
        events = list(
            BMWCarDataEvent.objects.filter(vehicle=vehicle, processed=False).order_by(
                "timestamp", "received_at", "id"
            )
        )
        if not events:
            continue

        process_vehicle_stream(vehicle, events, now)


def reconcile_same_day_range_splits(
    session_clusters: List[tuple[VehicleSession, List[BMWCarDataEvent]]],
):
    sessions_by_date: dict[date, list[tuple[VehicleSession, List[BMWCarDataEvent]]]] = (
        {}
    )
    for session, cluster in session_clusters:
        if (
            session.activity_type == VehicleSession.ActivityType.DRIVE
            and session.total_distance_km is not None
            and session.total_distance_km > 0
            and cluster
            and cluster[0].event_time is not None
        ):
            sessions_by_date.setdefault(cluster[0].event_time.date(), []).append(
                (session, cluster)
            )

    for sessions in sessions_by_date.values():
        measured_range_splits = [
            (session, cluster)
            for session, cluster in sessions
            if session.distance_split_source
            in {
                VehicleSession.DistanceSplitSource.BMW_REPORTED,
                VehicleSession.DistanceSplitSource.ELECTRIC_RANGE_DROP,
            }
            and session.electric_distance_km is not None
            and (
                session.distance_split_source
                == VehicleSession.DistanceSplitSource.BMW_REPORTED
                or session.electric_distance_km > 0
            )
        ]
        total_electric_km = sum(
            (session.electric_distance_km for session, _ in measured_range_splits),
            Decimal("0"),
        )
        total_distance_km = sum(
            (session.total_distance_km for session, _ in measured_range_splits),
            Decimal("0"),
        )
        if total_distance_km <= 0:
            continue

        same_day_electric_share = total_electric_km / total_distance_km
        for session, cluster in sessions:
            if session.distance_split_source not in {
                VehicleSession.DistanceSplitSource.ELECTRIC_RANGE_DROP,
                VehicleSession.DistanceSplitSource.SAME_DAY_PATTERN,
            } or (
                session.distance_split_source
                == VehicleSession.DistanceSplitSource.ELECTRIC_RANGE_DROP
                and session.electric_distance_km != 0
            ):
                continue

            electric_distance_km = min(
                session.total_distance_km,
                (session.total_distance_km * same_day_electric_share).quantize(
                    Decimal("0.01")
                ),
            )
            session.electric_distance_km = electric_distance_km
            session.petrol_distance_km = (
                session.total_distance_km - electric_distance_km
            ).quantize(Decimal("0.01"))
            session.distance_split_source = (
                VehicleSession.DistanceSplitSource.SAME_DAY_PATTERN
            )
            session.save(
                update_fields=[
                    "electric_distance_km",
                    "petrol_distance_km",
                    "distance_split_source",
                ]
            )


def process_vehicle_stream(
    vehicle: Vehicle, events: List[BMWCarDataEvent], now: timezone.datetime
):
    buffer: List[BMWCarDataEvent] = []
    in_drive = False
    in_charge = False
    ignition_off_at = None
    saw_summary = False
    last_odo_km: Optional[Decimal] = None
    last_lock_state: Optional[str] = None
    session_clusters: List[tuple[VehicleSession, List[BMWCarDataEvent]]] = []

    def flush(activity_override: Optional[str] = None):
        nonlocal buffer, in_drive, in_charge, ignition_off_at, saw_summary, last_odo_km, last_lock_state

        if buffer:
            cluster = buffer
            session = save_session(
                vehicle, cluster, activity_override=activity_override
            )
            if session is not None:
                session_clusters.append((session, cluster))

        buffer = []
        in_drive = False
        in_charge = False
        ignition_off_at = None
        saw_summary = False
        last_odo_km = None
        last_lock_state = None

    def _update_charge_flag(key_l: str, val_u: str):
        nonlocal in_charge

        if key_l == DESC_CHARGING_STATUS:
            if val_u in ACTIVE_CHARGE_STATUSES:
                in_charge = True

            elif val_u == "CHARGINGENDED":
                in_charge = False

        elif key_l == DESC_PORT_STATUS:
            if val_u == "CONNECTED":
                in_charge = True
            elif val_u == "DISCONNECTED":
                in_charge = False

    for ev in events:
        ev_time = ev.event_time
        key_lower = (ev.event_type or "").lower()
        raw_val, unit = _unwrap_event(ev)
        val_str = str(raw_val).strip().lower()
        val_upper = str(raw_val).strip().upper()
        cur_odo_km: Optional[Decimal] = None

        if key_lower in {DESC_ODOMETER, DESC_END_ODOMETER}:
            cur_odo_km = _to_km(_to_decimal(raw_val), unit)

        cur_lock_state = _lock_state(key_lower, val_str)

        if not buffer:
            buffer.append(ev)
            _update_charge_flag(key_lower, val_upper)

            if _is_drive_start(key_lower, val_str) or _is_summary_event(key_lower):
                in_drive = True

                if _is_summary_event(key_lower):
                    saw_summary = True

            if cur_odo_km is not None:
                last_odo_km = cur_odo_km

            if cur_lock_state:
                last_lock_state = cur_lock_state

            continue

        prev_time = buffer[-1].event_time
        odo_advanced = (
            cur_odo_km is not None
            and last_odo_km is not None
            and cur_odo_km > last_odo_km
        )

        # --- CASE 1: Currently inside a DRIVE cycle ---
        if in_drive:
            if ignition_off_at and (
                _is_drive_start(key_lower, val_str) or odo_advanced
            ):
                flush(VehicleSession.ActivityType.DRIVE)
                buffer.append(ev)
                _update_charge_flag(key_lower, val_upper)
                in_drive = True

                if cur_odo_km is not None:
                    last_odo_km = cur_odo_km

                if cur_lock_state:
                    last_lock_state = cur_lock_state

                continue

            # Absorb lock/unlock or summary events right after shutdown; flush on real gaps/other events
            if (
                ignition_off_at
                and (ev_time - ignition_off_at) > POST_SHUTDOWN_GRACE
                and not _is_summary_event(key_lower)
                and cur_lock_state is None
            ):
                flush(VehicleSession.ActivityType.DRIVE)
                buffer.append(ev)
                _update_charge_flag(key_lower, val_upper)

                if _is_drive_start(key_lower, val_str) or _is_summary_event(key_lower):
                    in_drive = True

                    if _is_summary_event(key_lower):
                        saw_summary = True

                if cur_odo_km is not None:
                    last_odo_km = cur_odo_km

                if cur_lock_state:
                    last_lock_state = cur_lock_state

                continue

            if (
                ignition_off_at is None
                and not odo_advanced
                and (ev_time - prev_time) > DRIVE_IDLE_TIMEOUT
            ):
                flush(VehicleSession.ActivityType.DRIVE)
                buffer.append(ev)
                _update_charge_flag(key_lower, val_upper)

                if _is_drive_start(key_lower, val_str) or _is_summary_event(key_lower):
                    in_drive = True

                    if _is_summary_event(key_lower):
                        saw_summary = True

                if cur_odo_km is not None:
                    last_odo_km = cur_odo_km

                if cur_lock_state:
                    last_lock_state = cur_lock_state

                continue

        # --- CASE 2: Outside a DRIVE cycle ---
        if not in_drive:
            # Merge pre-drive events into the upcoming DRIVE if within NON_DRIVE_GAP;
            # otherwise flush the older stationary cluster first.
            if _is_drive_start(key_lower, val_str) or odo_advanced:
                if (ev_time - prev_time) > NON_DRIVE_GAP:
                    flush(VehicleSession.ActivityType.CHARGE if in_charge else None)

                buffer.append(ev)
                _update_charge_flag(key_lower, val_upper)
                in_drive = True
                ignition_off_at = None

                if cur_odo_km is not None:
                    last_odo_km = cur_odo_km

                if cur_lock_state:
                    last_lock_state = cur_lock_state

                continue

            gap_limit = CHARGE_IDLE_TIMEOUT if in_charge else NON_DRIVE_GAP

            if (ev_time - prev_time) > gap_limit:
                flush(VehicleSession.ActivityType.CHARGE if in_charge else None)
                buffer.append(ev)
                _update_charge_flag(key_lower, val_upper)

                if _is_summary_event(key_lower):
                    in_drive = True
                    saw_summary = True

                if cur_odo_km is not None:
                    last_odo_km = cur_odo_km

                if cur_lock_state:
                    last_lock_state = cur_lock_state

                continue

        # --- Append to active buffer & update tracked state ---
        buffer.append(ev)
        _update_charge_flag(key_lower, val_upper)

        if cur_lock_state:
            last_lock_state = cur_lock_state

        if cur_odo_km is not None:
            if odo_advanced:
                in_drive = True
                ignition_off_at = None
            last_odo_km = cur_odo_km

        if _is_ignition_off(key_lower, val_str) and ignition_off_at is None:
            ignition_off_at = ev_time

        elif _is_summary_event(key_lower):
            saw_summary = True

            if not in_drive:
                in_drive = True

    if buffer:
        quiet_for = now - buffer[-1].event_time

        if in_drive:
            if (
                ignition_off_at and (saw_summary or quiet_for >= POST_SHUTDOWN_GRACE)
            ) or (ignition_off_at is None and quiet_for >= DRIVE_IDLE_TIMEOUT):
                flush(VehicleSession.ActivityType.DRIVE)

        elif in_charge:
            if quiet_for >= CHARGE_IDLE_TIMEOUT:
                flush(VehicleSession.ActivityType.CHARGE)

        elif quiet_for >= NON_DRIVE_GAP:
            flush()

    reconcile_same_day_range_splits(session_clusters)


@transaction.atomic
def save_session(
    vehicle: Vehicle,
    cluster: List[BMWCarDataEvent],
    activity_override: Optional[str] = None,
) -> Optional[VehicleSession]:
    merged_state = {}
    route_samples = []
    keys_seen = set()
    door_statuses = []

    odometers = []
    hv_soc_samples = []
    electric_ranges_km = []
    fuels_liters = []
    ect_temps = []

    end_segment_odo = None
    end_segment_soc = None
    ev_fraction_pct = None
    recup_rate = None
    ev_kwh_comfort = None
    avg_elec_kwh_per_100km = None
    sme_energy_deltas = []
    usable_battery_kwh = None
    recup_unit = ""
    is_charging = False
    saw_drive_signal = False
    engine_active_reported = False
    ice_engine_active = False

    for ev in cluster:
        key = ev.event_type or ""
        key_lower = key.lower()
        keys_seen.add(key_lower)

        val, unit = _unwrap_event(ev)
        merged_state[key] = {"value": val, "unit": unit} if unit else val
        num = _to_decimal(val)
        val_low = str(val).strip().lower()
        val_upper = str(val).strip().upper()

        if _is_drive_start(key_lower, val_low):
            saw_drive_signal = True

        if key_lower == DESC_ENGINE_ACTIVE:
            engine_active_reported = True
            ice_engine_active = ice_engine_active or val_low in TRUE_VALUES

        state = _lock_state(key_lower, val_low)

        if state:
            door_statuses.append(state)

        if key_lower == DESC_ODOMETER and num is not None:
            odometers.append(_to_km(num, unit))
        elif key_lower == DESC_END_ODOMETER and num is not None:
            end_segment_odo = _to_km(num, unit)
        elif key_lower == DESC_LIVE_HV_SOC and num is not None:
            hv_soc_samples.append((ev.event_time, num))
        elif key_lower == DESC_END_HV_SOC and num is not None:
            end_segment_soc = num
        elif key_lower == DESC_KOMBI_ELEC_RANGE and num is not None:
            range_km = _to_km(num, unit)

            if range_km is not None:
                electric_ranges_km.append(range_km)

        elif key_lower == DESC_REMAINING_FUEL and num is not None:
            fuel_val = _to_liters(num, unit)

            if fuel_val is not None:
                fuels_liters.append(fuel_val)

        elif key_lower == DESC_ENGINE_ECT and num is not None:
            ect_temps.append(num)
        elif key_lower == DESC_EV_FRACTION and num is not None:
            ev_fraction_pct = num
        elif key_lower == DESC_RECUP_TOTAL and num is not None:
            recup_rate = num
            recup_unit = unit
        elif key_lower == DESC_EV_ENERGY_COMFORT and num is not None:
            ev_kwh_comfort = num
        elif key_lower == DESC_AVG_ELEC_CONSUMPTION and num is not None:
            avg_elec_kwh_per_100km = num
        elif key_lower == DESC_SME_ENERGY_DELTA_FULL and num is not None:
            sme_energy_deltas.append(num)
        elif key_lower == DESC_BATTERY_MAX_ENERGY and num is not None:
            usable_battery_kwh = num

        if (
            key_lower == DESC_CHARGING_STATUS and val_upper in ACTIVE_CHARGE_STATUSES
        ) or (key_lower == DESC_PORT_STATUS and val_upper == "CONNECTED"):
            is_charging = True

        if key_lower in {
            DESC_LAT,
            DESC_LON,
            # DESC_ALTITUDE,
            DESC_LIVE_HV_SOC,
            DESC_ENGINE_ACTIVE,
            DESC_KOMBI_ELEC_RANGE,
        }:
            route_samples.append(
                {
                    "ts": ev.event_time.isoformat() if ev.event_time else None,
                    "key": key,
                    "value": val,
                    "unit": unit,
                }
            )

    if end_segment_odo is not None:
        odometers.append(end_segment_odo)

    start_odo = min(odometers) if odometers else None
    end_odo = max(odometers) if odometers else None
    total_dist_km = (
        (end_odo - start_odo)
        if (start_odo is not None and end_odo is not None)
        else None
    )
    has_distance_gain = total_dist_km is not None and total_dist_km > 0

    has_access_key = any(
        token in k
        for k in keys_seen
        for token in ("door", "trunk", "hood", "window", "sunroof", "roof")
    )

    # Classify session: DRIVE and CHARGE take priority over merged door/lock events
    if activity_override:
        activity = activity_override
    elif saw_drive_signal or (keys_seen & SUMMARY_DESCRIPTORS) or has_distance_gain:
        activity = VehicleSession.ActivityType.DRIVE
    elif is_charging:
        activity = VehicleSession.ActivityType.CHARGE
    elif door_statuses:
        activity = (
            VehicleSession.ActivityType.UNLOCK
            if door_statuses[-1] == "UNLOCK"
            else VehicleSession.ActivityType.LOCK
        )
    elif has_access_key:
        activity = VehicleSession.ActivityType.ACCESS
    else:
        activity = VehicleSession.ActivityType.OTHER

    if activity in {
        VehicleSession.ActivityType.LOCK,
        VehicleSession.ActivityType.UNLOCK,
        VehicleSession.ActivityType.ACCESS,
    }:
        BMWCarDataEvent.objects.filter(id__in=[e.id for e in cluster]).update(
            processed=True,
            session=None,
        )
        return None

    electric_dist_km = None
    distance_split_source = ""

    if (
        total_dist_km is not None
        and ev_fraction_pct is not None
        and Decimal("0") <= ev_fraction_pct <= Decimal("100")
    ):
        electric_dist_km = (total_dist_km * ev_fraction_pct / Decimal("100")).quantize(
            Decimal("0.01")
        )
        distance_split_source = VehicleSession.DistanceSplitSource.BMW_REPORTED
    elif (
        activity == VehicleSession.ActivityType.DRIVE
        and total_dist_km is not None
        and total_dist_km > 0
        and len(electric_ranges_km) >= 2
        and electric_ranges_km[0] >= electric_ranges_km[-1] >= 0
    ):
        range_drop_km = electric_ranges_km[0] - electric_ranges_km[-1]
        electric_dist_km = min(total_dist_km, range_drop_km).quantize(Decimal("0.01"))
        distance_split_source = VehicleSession.DistanceSplitSource.ELECTRIC_RANGE_DROP

    petrol_dist_km = None

    if total_dist_km is not None and electric_dist_km is not None:
        petrol_dist_km = max(Decimal("0"), total_dist_km - electric_dist_km).quantize(
            Decimal("0.01")
        )
    cluster_start = cluster[0].event_time
    cluster_end = cluster[-1].event_time

    if hv_soc_samples:
        if activity == VehicleSession.ActivityType.DRIVE:
            end_candidates = [
                (timestamp, soc)
                for timestamp, soc in hv_soc_samples
                if cluster_end - SOC_BOUNDARY_WINDOW <= timestamp <= cluster_end
            ]
            end_candidate_times = {timestamp for timestamp, _ in end_candidates}
            start_candidates = [
                (timestamp, soc)
                for timestamp, soc in hv_soc_samples
                if (
                    cluster_start <= timestamp <= cluster_start + SOC_BOUNDARY_WINDOW
                    and timestamp not in end_candidate_times
                )
            ]
            start_soc = start_candidates[-1][1] if start_candidates else None
            end_soc = (
                end_segment_soc
                if end_segment_soc is not None
                else (end_candidates[-1][1] if end_candidates else None)
            )

        else:
            start_soc = hv_soc_samples[0][1]
            end_soc = (
                end_segment_soc
                if end_segment_soc is not None
                else hv_soc_samples[-1][1]
            )
    elif activity == VehicleSession.ActivityType.CHARGE:
        start_soc = None
        end_soc = end_segment_soc
    else:
        start_soc = None
        end_soc = end_segment_soc

    electric_kwh = ev_kwh_comfort
    electric_kwh_source = (
        VehicleSession.ElectricEnergySource.BMW_REPORTED
        if electric_kwh is not None
        else ""
    )
    if (
        electric_kwh is None
        and activity == VehicleSession.ActivityType.DRIVE
        and avg_elec_kwh_per_100km is not None
        and electric_dist_km is not None
    ):
        electric_kwh = (
            avg_elec_kwh_per_100km * electric_dist_km / Decimal("100")
        ).quantize(Decimal("0.01"))
        electric_kwh_source = VehicleSession.ElectricEnergySource.AVG_CONSUMPTION

    if (
        electric_kwh is None
        and activity == VehicleSession.ActivityType.CHARGE
        and start_soc is not None
        and end_soc is not None
        and usable_battery_kwh is not None
        and end_soc > start_soc
    ):
        electric_kwh = (
            (end_soc - start_soc) / Decimal("100") * usable_battery_kwh
        ).quantize(Decimal("0.01"))
        electric_kwh_source = VehicleSession.ElectricEnergySource.SOC_CHANGE

    if (
        electric_kwh is None
        and activity == VehicleSession.ActivityType.CHARGE
        and len(sme_energy_deltas) >= 2
        and sme_energy_deltas[0] > sme_energy_deltas[-1]
    ):
        electric_kwh = (sme_energy_deltas[0] - sme_energy_deltas[-1]).quantize(
            Decimal("0.01")
        )
        electric_kwh_source = VehicleSession.ElectricEnergySource.SME_ENERGY_DELTA

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
    fuel_level_start_liters = fuels_liters[0] if fuels_liters else None
    fuel_level_end_liters = fuels_liters[-1] if fuels_liters else None
    fuel_liters = None
    fuel_levels_decreased = all(
        previous >= current for previous, current in zip(fuels_liters, fuels_liters[1:])
    )

    if (
        len(fuels_liters) >= 2
        and fuels_liters[0] > fuels_liters[-1]
        and fuel_levels_decreased
    ):
        fuel_liters = (fuels_liters[0] - fuels_liters[-1]).quantize(Decimal("0.01"))

    ect_rise = (
        (max(ect_temps) - min(ect_temps)) if len(ect_temps) >= 2 else Decimal("0")
    )

    if (
        ice_engine_active
        or (fuel_liters and fuel_liters > 0)
        or ect_rise > Decimal("5")
    ):
        ice_engine_ran = True
    elif engine_active_reported:
        ice_engine_ran = False
    else:
        ice_engine_ran = False

    route_points = (
        _build_route_points(route_samples)
        if activity == VehicleSession.ActivityType.DRIVE
        else []
    )

    session = VehicleSession.objects.create(
        vehicle=vehicle,
        activity_type=activity,
        started_at=cluster[0].event_time,
        ended_at=cluster[-1].event_time,
        event_count=len(cluster),
        merged_state=json.loads(json.dumps(merged_state, cls=DjangoJSONEncoder)),
        start_odometer_km=start_odo,
        end_odometer_km=end_odo,
        total_distance_km=total_dist_km,
        electric_distance_km=electric_dist_km,
        petrol_distance_km=petrol_dist_km,
        distance_split_source=distance_split_source,
        fuel_consumed_liters=fuel_liters,
        fuel_level_start_liters=fuel_level_start_liters,
        fuel_level_end_liters=fuel_level_end_liters,
        electric_consumed_kwh=electric_kwh,
        electric_consumed_kwh_source=electric_kwh_source,
        recuperated_kwh=recuperated_kwh,
        ice_engine_ran=ice_engine_ran,
        start_soc=start_soc,
        end_soc=end_soc,
        route_points=json.loads(json.dumps(route_points, cls=DjangoJSONEncoder)),
    )

    BMWCarDataEvent.objects.filter(id__in=[e.id for e in cluster]).update(
        processed=True,
        session=session,
    )

    return session
