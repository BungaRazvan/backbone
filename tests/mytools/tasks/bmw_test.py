import json
import pytest

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from mytools.models import BMWCarDataEvent, Vehicle, VehicleSession
from mytools.tasks.bmw.merge_bmw_events import (
    DESC_EV_FRACTION,
    DESC_IGNITION,
    DESC_ODOMETER,
    merge_bmw_events,
)
from mytools.tasks.bmw.process_bmw_mqtt_event import process_bmw_mqtt_event


@pytest.fixture
def bmw_vehicle(db):
    return Vehicle.objects.create(vin="WBA00000000000001", make="BMW", model="i3")


def test_process_bmw_mqtt_event_saves_payload_for_known_vehicle(bmw_vehicle):
    payload = {
        "vin": bmw_vehicle.vin,
        "data": {
            "vehicle.cabin.door.isopen": {
                "value": True,
                "timestamp": "2026-01-02T03:04:05Z",
            }
        },
    }

    process_bmw_mqtt_event("bmw/vehicles", json.dumps(payload))

    event = BMWCarDataEvent.objects.get()
    assert event.vehicle == bmw_vehicle
    assert event.event_type == "vehicle.cabin.door.isopen"
    assert event.timestamp == timezone.datetime(
        2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc
    )
    assert event.payload == payload
    assert event.processed is False


def test_process_bmw_mqtt_event_uses_topic_vin_and_millisecond_timestamp():
    timestamp = 1_700_000_000_000
    vehicle = Vehicle.objects.create(vin="WBA00000000000002", make="BMW", model="i3")

    process_bmw_mqtt_event(
        f"bmw/vehicles/{vehicle.vin}",
        json.dumps({"timestamp": timestamp}),
    )

    event = BMWCarDataEvent.objects.get()
    assert event.vehicle == vehicle
    assert event.timestamp == timezone.datetime.fromtimestamp(
        timestamp / 1000, tz=timezone.utc
    )
    assert event.event_type is None


@pytest.mark.parametrize(
    ("topic", "raw_payload"),
    [
        ("bmw/vehicles/WBA00000000000003", "{"),
        ("bmw/status/WBA00000000000003", "{}"),
        ("bmw/vehicles/WBA00000000000003", '{"connected": true}'),
    ],
)
def test_process_bmw_mqtt_event_ignores_invalid_and_status_messages(topic, raw_payload):
    process_bmw_mqtt_event(topic, raw_payload)

    assert BMWCarDataEvent.objects.count() == 0


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
    assert BMWCarDataEvent.objects.filter(
        pk__in=[event.pk for event in events],
        session=session,
        processed=True,
    ).count() == len(signals)
