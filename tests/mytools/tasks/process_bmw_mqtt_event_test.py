import json

import pytest
from django.contrib import admin
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.utils import timezone

from mytools.admin.vehicle import VehicleSessionAdmin
from mytools.models import BMWCarDataEvent, Vehicle, VehicleSession
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


def test_vehicle_session_admin_labels_charge_energy_as_charged(bmw_vehicle):
    session = VehicleSession.objects.create(
        vehicle=bmw_vehicle,
        activity_type=VehicleSession.ActivityType.CHARGE,
        started_at=timezone.now(),
        ended_at=timezone.now(),
    )
    model_admin = VehicleSessionAdmin(VehicleSession, admin.site)
    request = RequestFactory().get("/admin/")
    request.user = AnonymousUser()

    form = model_admin.get_form(request, obj=session)

    assert form.base_fields["electric_consumed_kwh"].label == "Electric charged kWh"
