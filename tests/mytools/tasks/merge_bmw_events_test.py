from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from mytools.models import BMWCarDataEvent, Vehicle, VehicleSession
from mytools.tasks.bmw.merge_bmw_events import (
    DESC_ENGINE_ACTIVE,
    DESC_ENGINE_ECT,
    DESC_EV_ENERGY_COMFORT,
    DESC_EV_FRACTION,
    DESC_IGNITION,
    DESC_LIVE_HV_SOC,
    DESC_ODOMETER,
    DESC_PORT_STATUS,
    merge_bmw_events,
)


@pytest.fixture
def bmw_vehicle(db):
    return Vehicle.objects.create(vin="WBA00000000000001", make="BMW", model="i3")



def test_merge_bmw_events_creates_access_session_and_skips_other_vehicles(
    bmw_vehicle,
):
    timestamp = timezone.now() - timedelta(minutes=10)
    access_event = BMWCarDataEvent.objects.create(
        vehicle=bmw_vehicle,
        event_type="vehicle.cabin.door.isopen",
        timestamp=timestamp,
        payload={"value": True},
    )
    inactive_vehicle = Vehicle.objects.create(
        vin="WBA00000000000004",
        make="BMW",
        model="i3",
        is_active=False,
    )
    inactive_event = BMWCarDataEvent.objects.create(
        vehicle=inactive_vehicle,
        event_type="vehicle.cabin.door.isopen",
        timestamp=timestamp,
        payload={"value": True},
    )
    other_make = Vehicle.objects.create(
        vin="OTHER0000000000001", make="Other", model="Car"
    )
    other_make_event = BMWCarDataEvent.objects.create(
        vehicle=other_make,
        event_type="vehicle.cabin.door.isopen",
        timestamp=timestamp,
        payload={"value": True},
    )

    merge_bmw_events()

    session = VehicleSession.objects.get()
    assert session.vehicle == bmw_vehicle
    assert session.activity_type == VehicleSession.ActivityType.ACCESS
    assert session.event_count == 1
    access_event.refresh_from_db()
    assert access_event.processed is True
    assert access_event.session == session
    inactive_event.refresh_from_db()
    other_make_event.refresh_from_db()
    assert inactive_event.processed is False
    assert other_make_event.processed is False


def test_merge_bmw_events_does_not_apply_drive_grace_to_access_session(bmw_vehicle):
    start = timezone.now() - timedelta(minutes=30)
    signals = [
        (0, "vehicle.cabin.door.isopen", {"value": True}),
        (1, DESC_IGNITION, {"value": False}),
        (4, "vehicle.vehicle.speed", {"value": 0, "unit": "km/h"}),
    ]
    events = [
        BMWCarDataEvent.objects.create(
            vehicle=bmw_vehicle,
            event_type=event_type,
            timestamp=start + timedelta(minutes=minutes),
            payload=payload,
        )
        for minutes, event_type, payload in signals
    ]

    merge_bmw_events()

    session = VehicleSession.objects.get()
    assert session.activity_type == VehicleSession.ActivityType.ACCESS
    assert session.event_count == len(signals)
    assert BMWCarDataEvent.objects.filter(
        pk__in=[event.pk for event in events],
        session=session,
        processed=True,
    ).count() == len(signals)


def test_merge_bmw_events_saves_drive_metrics(bmw_vehicle):
    start = timezone.now() - timedelta(minutes=20)
    signals = [
        (DESC_IGNITION, {"value": True}),
        (DESC_ODOMETER, {"value": 1000, "unit": "km"}),
        (DESC_ODOMETER, {"value": 1012, "unit": "km"}),
        (DESC_EV_FRACTION, {"value": 50, "unit": "%"}),
        ("vehicle.drivetrain.avgElectricRangeConsumption", {"value": 23.15}),
        (DESC_IGNITION, {"value": False}),
        (DESC_EV_FRACTION, {"value": 50, "unit": "%"}),
    ]
    events = [
        BMWCarDataEvent.objects.create(
            vehicle=bmw_vehicle,
            event_type=event_type,
            timestamp=start + timedelta(minutes=offset),
            payload=payload,
        )
        for offset, (event_type, payload) in enumerate(signals)
    ]

    merge_bmw_events()

    session = VehicleSession.objects.get()
    assert session.activity_type == VehicleSession.ActivityType.DRIVE
    assert session.event_count == len(signals)
    assert session.start_odometer_km == Decimal("1000.0")
    assert session.end_odometer_km == Decimal("1012.0")
    assert session.total_distance_km == Decimal("12.00")
    assert session.electric_distance_km == Decimal("6.00")
    assert session.petrol_distance_km == Decimal("6.00")
    assert (
        session.distance_split_source == VehicleSession.DistanceSplitSource.BMW_REPORTED
    )
    assert session.electric_consumed_kwh == Decimal("1.39")
    assert (
        session.electric_consumed_kwh_source
        == VehicleSession.ElectricEnergySource.AVG_CONSUMPTION
    )
    assert BMWCarDataEvent.objects.filter(
        pk__in=[event.pk for event in events],
        session=session,
        processed=True,
    ).count() == len(signals)


def test_merge_bmw_events_saves_bmw_reported_electric_energy(bmw_vehicle):
    start = timezone.now() - timedelta(minutes=20)
    signals = [
        (DESC_IGNITION, {"value": True}),
        (DESC_EV_ENERGY_COMFORT, {"value": 1.75, "unit": "kwh"}),
        (DESC_IGNITION, {"value": False}),
    ]
    for offset, (event_type, payload) in enumerate(signals):
        BMWCarDataEvent.objects.create(
            vehicle=bmw_vehicle,
            event_type=event_type,
            timestamp=start + timedelta(minutes=offset),
            payload=payload,
        )

    merge_bmw_events()

    session = VehicleSession.objects.get()
    assert session.electric_consumed_kwh == Decimal("1.75")
    assert (
        session.electric_consumed_kwh_source
        == VehicleSession.ElectricEnergySource.BMW_REPORTED
    )


def test_merge_bmw_events_does_not_estimate_charging_energy_from_soc(bmw_vehicle):
    start = timezone.now() - timedelta(minutes=30)
    signals = [
        (
            0,
            "vehicle.drivetrain.electricEngine.charging.status",
            {"value": "CHARGINGACTIVE"},
        ),
        (1, DESC_LIVE_HV_SOC, {"value": 5.5, "unit": "percent"}),
        (10, DESC_LIVE_HV_SOC, {"value": 67.6, "unit": "percent"}),
        (
            11,
            "vehicle.drivetrain.batteryManagement.maxEnergy",
            {"value": 8.82, "unit": "kwh"},
        ),
        (
            12,
            "vehicle.drivetrain.electricEngine.charging.status",
            {"value": "NOCHARGING"},
        ),
        (13, DESC_PORT_STATUS, {"value": "DISCONNECTED"}),
    ]
    for offset, event_type, payload in signals:
        BMWCarDataEvent.objects.create(
            vehicle=bmw_vehicle,
            event_type=event_type,
            timestamp=start + timedelta(minutes=offset),
            payload=payload,
        )

    merge_bmw_events()

    session = VehicleSession.objects.get()
    assert session.activity_type == VehicleSession.ActivityType.CHARGE
    assert session.start_soc == Decimal("5.5")
    assert session.end_soc == Decimal("67.6")
    assert session.electric_consumed_kwh == Decimal("5.48")
    assert (
        session.electric_consumed_kwh_source
        == VehicleSession.ElectricEnergySource.SOC_CHANGE
    )


def test_merge_bmw_events_does_not_reuse_stale_soc(bmw_vehicle):
    now = timezone.now()
    VehicleSession.objects.create(
        vehicle=bmw_vehicle,
        activity_type=VehicleSession.ActivityType.CHARGE,
        started_at=now - timedelta(days=2),
        ended_at=now - timedelta(days=2),
        start_soc=Decimal("5.50"),
        end_soc=Decimal("67.60"),
    )
    event = BMWCarDataEvent.objects.create(
        vehicle=bmw_vehicle,
        event_type="vehicle.cabin.door.status",
        timestamp=now - timedelta(minutes=10),
        payload={"value": "LOCKED"},
    )

    merge_bmw_events()

    session = VehicleSession.objects.filter(
        vehicle=bmw_vehicle,
        activity_type=VehicleSession.ActivityType.LOCK,
    ).get()
    assert session.start_soc is None
    assert session.end_soc is None
    event.refresh_from_db()
    assert event.processed is True


def test_merge_bmw_events_uses_end_soc_only_when_reading_is_near_trip_end(
    bmw_vehicle,
):
    start = timezone.now() - timedelta(minutes=30)
    events = [
        (0, DESC_IGNITION, {"value": True}),
        (5, DESC_ODOMETER, {"value": 1000, "unit": "km"}),
        (20, DESC_LIVE_HV_SOC, {"value": 36.2, "unit": "percent"}),
        (21, DESC_ODOMETER, {"value": 1009, "unit": "km"}),
        (22, DESC_IGNITION, {"value": False}),
    ]

    created = [
        BMWCarDataEvent.objects.create(
            vehicle=bmw_vehicle,
            event_type=event_type,
            timestamp=start + timedelta(minutes=offset),
            payload=payload,
        )
        for offset, event_type, payload in events
    ]

    merge_bmw_events()

    session = VehicleSession.objects.get()
    assert session.activity_type == VehicleSession.ActivityType.DRIVE
    assert session.start_soc is None
    assert session.end_soc == Decimal("36.20")
    assert BMWCarDataEvent.objects.filter(
        pk__in=[event.pk for event in created],
        session=session,
        processed=True,
    ).count() == len(created)


def test_merge_bmw_events_does_not_carry_soc_from_lock_to_next_drive(
    bmw_vehicle,
):
    start = timezone.now() - timedelta(minutes=60)
    lock_soc = BMWCarDataEvent.objects.create(
        vehicle=bmw_vehicle,
        event_type=DESC_LIVE_HV_SOC,
        timestamp=start,
        payload={"value": 32.3, "unit": "percent"},
    )
    lock_event = BMWCarDataEvent.objects.create(
        vehicle=bmw_vehicle,
        event_type="vehicle.cabin.door.status",
        timestamp=start + timedelta(minutes=1),
        payload={"value": "SECURED"},
    )
    drive_start = BMWCarDataEvent.objects.create(
        vehicle=bmw_vehicle,
        event_type=DESC_ODOMETER,
        timestamp=start + timedelta(minutes=30),
        payload={"value": 1000, "unit": "km"},
    )
    drive_end = BMWCarDataEvent.objects.create(
        vehicle=bmw_vehicle,
        event_type=DESC_ODOMETER,
        timestamp=start + timedelta(minutes=40),
        payload={"value": 1003, "unit": "km"},
    )
    end_soc = BMWCarDataEvent.objects.create(
        vehicle=bmw_vehicle,
        event_type=DESC_LIVE_HV_SOC,
        timestamp=start + timedelta(minutes=40),
        payload={"value": 17.7, "unit": "percent"},
    )

    merge_bmw_events()

    drive = VehicleSession.objects.filter(
        vehicle=bmw_vehicle,
        activity_type=VehicleSession.ActivityType.DRIVE,
    ).get()
    assert drive.start_soc is None
    assert drive.end_soc == Decimal("17.70")
    assert (
        BMWCarDataEvent.objects.filter(
            pk__in=[
                lock_soc.pk,
                lock_event.pk,
                drive_start.pk,
                drive_end.pk,
                end_soc.pk,
            ],
            processed=True,
        ).count()
        == 5
    )


def test_merge_bmw_events_estimates_electric_distance_from_range_drop(
    bmw_vehicle,
):
    start = timezone.now() - timedelta(minutes=30)
    signals = [
        (0, DESC_IGNITION, {"value": True}),
        (1, DESC_ODOMETER, {"value": 1000, "unit": "km"}),
        (
            1,
            "vehicle.drivetrain.electricEngine.kombiRemainingElectricRange",
            {"value": 25, "unit": "km"},
        ),
        (10, DESC_ENGINE_ECT, {"value": 16, "unit": "celsius"}),
        (
            20,
            "vehicle.drivetrain.electricEngine.kombiRemainingElectricRange",
            {"value": 9, "unit": "km"},
        ),
        (21, DESC_ODOMETER, {"value": 1009, "unit": "km"}),
        (22, DESC_IGNITION, {"value": False}),
    ]
    for offset, event_type, payload in signals:
        BMWCarDataEvent.objects.create(
            vehicle=bmw_vehicle,
            event_type=event_type,
            timestamp=start + timedelta(minutes=offset),
            payload=payload,
        )

    merge_bmw_events()

    session = VehicleSession.objects.get()
    assert session.total_distance_km == Decimal("9.00")
    assert session.electric_distance_km == Decimal("9.00")
    assert session.petrol_distance_km == Decimal("0.00")
    assert (
        session.distance_split_source
        == VehicleSession.DistanceSplitSource.ELECTRIC_RANGE_DROP
    )
    assert session.ice_engine_ran is False


def test_merge_bmw_events_estimates_petrol_distance_as_trip_remainder(
    bmw_vehicle,
):
    start = timezone.now() - timedelta(minutes=30)
    signals = [
        (0, DESC_IGNITION, {"value": True}),
        (1, DESC_ODOMETER, {"value": 1000, "unit": "km"}),
        (
            1,
            "vehicle.drivetrain.electricEngine.kombiRemainingElectricRange",
            {"value": 3, "unit": "km"},
        ),
        (
            1,
            "vehicle.drivetrain.avgElectricRangeConsumption",
            {"value": 23.15, "unit": "kwh/100km"},
        ),
        (
            10,
            "vehicle.drivetrain.electricEngine.kombiRemainingElectricRange",
            {"value": 0, "unit": "km"},
        ),
        (
            11,
            "vehicle.drivetrain.electricEngine.kombiRemainingElectricRange",
            {"value": 1, "unit": "km"},
        ),
        (
            12,
            "vehicle.drivetrain.electricEngine.kombiRemainingElectricRange",
            {"value": 0, "unit": "km"},
        ),
        (13, DESC_ODOMETER, {"value": 1011, "unit": "km"}),
        (14, DESC_IGNITION, {"value": False}),
    ]
    for offset, event_type, payload in signals:
        BMWCarDataEvent.objects.create(
            vehicle=bmw_vehicle,
            event_type=event_type,
            timestamp=start + timedelta(minutes=offset),
            payload=payload,
        )

    merge_bmw_events()

    session = VehicleSession.objects.filter(
        activity_type=VehicleSession.ActivityType.DRIVE,
    ).get()
    assert session.electric_distance_km == Decimal("3.00")
    assert session.petrol_distance_km == Decimal("8.00")
    assert session.electric_consumed_kwh == Decimal("0.69")
    assert (
        session.distance_split_source
        == VehicleSession.DistanceSplitSource.ELECTRIC_RANGE_DROP
    )


def test_zero_range_trip_uses_same_day_range_pattern(bmw_vehicle):
    start = timezone.now() - timedelta(hours=1)
    signals = [
        (0, DESC_IGNITION, {"value": True}),
        (1, DESC_ODOMETER, {"value": 1000, "unit": "km"}),
        (
            2,
            "vehicle.drivetrain.electricEngine.kombiRemainingElectricRange",
            {"value": 10, "unit": "km"},
        ),
        (
            8,
            "vehicle.drivetrain.electricEngine.kombiRemainingElectricRange",
            {"value": 5, "unit": "km"},
        ),
        (9, DESC_ODOMETER, {"value": 1010, "unit": "km"}),
        (10, DESC_IGNITION, {"value": False}),
        (20, DESC_IGNITION, {"value": True}),
        (21, DESC_ODOMETER, {"value": 1010, "unit": "km"}),
        (
            22,
            "vehicle.drivetrain.electricEngine.kombiRemainingElectricRange",
            {"value": 0, "unit": "km"},
        ),
        (
            25,
            "vehicle.drivetrain.electricEngine.kombiRemainingElectricRange",
            {"value": 0, "unit": "km"},
        ),
        (26, DESC_ODOMETER, {"value": 1013, "unit": "km"}),
        (27, DESC_IGNITION, {"value": False}),
    ]
    for offset, event_type, payload in signals:
        BMWCarDataEvent.objects.create(
            vehicle=bmw_vehicle,
            event_type=event_type,
            timestamp=start + timedelta(minutes=offset),
            payload=payload,
        )

    merge_bmw_events()

    trips = list(
        VehicleSession.objects.filter(
            activity_type=VehicleSession.ActivityType.DRIVE,
        ).order_by("started_at")
    )
    assert len(trips) == 2
    assert trips[0].electric_distance_km == Decimal("5.00")
    assert trips[1].electric_distance_km == Decimal("1.50")
    assert trips[1].petrol_distance_km == Decimal("1.50")
    assert (
        trips[1].distance_split_source
        == VehicleSession.DistanceSplitSource.SAME_DAY_PATTERN
    )


def test_merge_bmw_events_keeps_zero_range_trip_as_estimated_split(bmw_vehicle):
    start = timezone.now() - timedelta(minutes=30)
    signals = [
        (0, DESC_IGNITION, {"value": True}),
        (1, DESC_ODOMETER, {"value": 1000, "unit": "km"}),
        (
            1,
            "vehicle.drivetrain.electricEngine.kombiRemainingElectricRange",
            {"value": 0, "unit": "km"},
        ),
        (
            5,
            "vehicle.drivetrain.electricEngine.kombiRemainingElectricRange",
            {"value": 0, "unit": "km"},
        ),
        (6, DESC_ODOMETER, {"value": 1003, "unit": "km"}),
        (7, DESC_IGNITION, {"value": False}),
    ]
    for offset, event_type, payload in signals:
        BMWCarDataEvent.objects.create(
            vehicle=bmw_vehicle,
            event_type=event_type,
            timestamp=start + timedelta(minutes=offset),
            payload=payload,
        )

    merge_bmw_events()

    session = VehicleSession.objects.filter(
        activity_type=VehicleSession.ActivityType.DRIVE,
    ).get()
    assert session.electric_distance_km == Decimal("0.00")
    assert session.petrol_distance_km == Decimal("3.00")
    assert (
        session.distance_split_source
        == VehicleSession.DistanceSplitSource.ELECTRIC_RANGE_DROP
    )
    assert session.ice_engine_ran is False


def test_merge_bmw_events_splits_out_fuel_level_rise_without_counting_consumption(
    bmw_vehicle,
):
    start = timezone.now() - timedelta(minutes=30)
    signals = [
        (0, DESC_IGNITION, {"value": True}),
        (
            1,
            "vehicle.drivetrain.fuelSystem.remainingFuel",
            {"value": 15, "unit": "l"},
        ),
        (
            5,
            "vehicle.drivetrain.fuelSystem.remainingFuel",
            {"value": 38, "unit": "l"},
        ),
        (
            10,
            "vehicle.drivetrain.fuelSystem.remainingFuel",
            {"value": 39, "unit": "l"},
        ),
        (
            15,
            "vehicle.drivetrain.fuelSystem.remainingFuel",
            {"value": 38, "unit": "l"},
        ),
        (16, DESC_IGNITION, {"value": False}),
    ]
    for offset, event_type, payload in signals:
        BMWCarDataEvent.objects.create(
            vehicle=bmw_vehicle,
            event_type=event_type,
            timestamp=start + timedelta(minutes=offset),
            payload=payload,
        )

    merge_bmw_events()

    sessions = list(VehicleSession.objects.order_by("started_at"))
    drive = next(
        session
        for session in sessions
        if session.activity_type == VehicleSession.ActivityType.DRIVE
    )
    after_refuel_snapshot = next(
        session
        for session in sessions
        if session.activity_type == VehicleSession.ActivityType.OTHER
    )
    assert drive.fuel_level_start_liters == Decimal("15.00")
    assert drive.fuel_level_end_liters == Decimal("15.00")
    assert drive.fuel_consumed_liters is None
    assert after_refuel_snapshot.fuel_level_start_liters == Decimal("38.00")
    assert after_refuel_snapshot.fuel_level_end_liters == Decimal("38.00")


def test_merge_bmw_events_splits_drive_at_large_fuel_level_jump(bmw_vehicle):
    start = timezone.now() - timedelta(minutes=30)
    signals = [
        (0, DESC_IGNITION, {"value": True}),
        (1, DESC_ODOMETER, {"value": 106593, "unit": "km"}),
        (
            1,
            "vehicle.drivetrain.fuelSystem.remainingFuel",
            {"value": 15, "unit": "l"},
        ),
        (5, DESC_ODOMETER, {"value": 106594, "unit": "km"}),
        (
            5,
            "vehicle.drivetrain.fuelSystem.remainingFuel",
            {"value": 15, "unit": "l"},
        ),
        (
            6,
            "vehicle.drivetrain.fuelSystem.remainingFuel",
            {"value": 38, "unit": "l"},
        ),
        (6, DESC_ODOMETER, {"value": 106594, "unit": "km"}),
        (8, "vehicle.cabin.door.status", {"value": "LOCKED"}),
        (9, DESC_ODOMETER, {"value": 106597, "unit": "km"}),
        (12, DESC_ODOMETER, {"value": 106600, "unit": "km"}),
        (15, DESC_ODOMETER, {"value": 106604, "unit": "km"}),
        (
            15,
            "vehicle.drivetrain.fuelSystem.remainingFuel",
            {"value": 38, "unit": "l"},
        ),
        (16, DESC_IGNITION, {"value": False}),
    ]
    events = [
        BMWCarDataEvent.objects.create(
            vehicle=bmw_vehicle,
            event_type=event_type,
            timestamp=start + timedelta(minutes=offset),
            payload=payload,
        )
        for offset, event_type, payload in signals
    ]

    merge_bmw_events()

    trips = list(
        VehicleSession.objects.filter(
            activity_type=VehicleSession.ActivityType.DRIVE,
        ).order_by("started_at")
    )
    assert len(trips) == 2
    assert trips[0].total_distance_km == Decimal("1.00")
    assert trips[0].fuel_level_start_liters == Decimal("15.00")
    assert trips[0].fuel_level_end_liters == Decimal("15.00")
    assert trips[1].total_distance_km == Decimal("10.00")
    assert trips[1].fuel_level_start_liters == Decimal("38.00")
    assert trips[1].fuel_level_end_liters == Decimal("38.00")
    assert BMWCarDataEvent.objects.filter(
        pk__in=[event.pk for event in events],
        processed=True,
    ).count() == len(events)


def test_merge_bmw_events_marks_ice_when_bmw_reports_engine_active(bmw_vehicle):
    start = timezone.now() - timedelta(minutes=30)
    BMWCarDataEvent.objects.create(
        vehicle=bmw_vehicle,
        event_type=DESC_ENGINE_ACTIVE,
        timestamp=start,
        payload={"value": True},
    )

    merge_bmw_events()

    session = VehicleSession.objects.get()
    assert session.activity_type == VehicleSession.ActivityType.DRIVE
    assert session.ice_engine_ran is True
