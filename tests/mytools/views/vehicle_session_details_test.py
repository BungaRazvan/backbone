from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from common.auth.decorators import validate_arguments
from mytools.models import VehicleSession
from mytools.views.vehicle.session_details import (
    ArgsGet,
    VehicleSessionDetailsSerializer,
)


def _signal(value, ts, unit=""):
    return {"value": value, "unit": unit, "ts": ts}


def _route_point(ts, lat, lon, signals=None):
    return {"ts": ts, "lat": lat, "lon": lon, "signals": signals or {}}


def test_session_ids_query_parameter_accepts_a_single_id():
    @validate_arguments(ArgsGet)
    def view(request, args):
        return args

    request = Request(APIRequestFactory().get("/vehicle/session_details?ids=20"))

    assert view(request).ids == [20]


def test_session_ids_query_parameter_accepts_comma_separated_ids():
    @validate_arguments(ArgsGet)
    def view(request, args):
        return args

    request = Request(
        APIRequestFactory().get("/vehicle/session_details", {"ids": "19,20"})
    )

    assert view(request).ids == [19, 20]


def test_route_modes_follow_engine_state_changes_within_trip():
    times = [f"2026-01-01T10:0{i}:00+00:00" for i in range(4)]
    session = VehicleSession(
        route_points=[
            _route_point(
                times[0],
                51.5,
                -0.1,
                {"engine_active": _signal(False, times[0])},
            ),
            _route_point(
                times[1],
                51.6,
                -0.2,
                {"engine_active": _signal(True, times[1])},
            ),
            _route_point(
                times[2],
                51.7,
                -0.3,
                {"engine_active": _signal(False, times[2])},
            ),
            _route_point(
                times[3],
                51.8,
                -0.4,
                {"engine_active": _signal(False, times[3])},
            ),
        ],
    )

    segments = VehicleSessionDetailsSerializer().get_route_segments(session)

    assert [segment["mode"] for segment in segments] == ["EV", "ICE", "EV"]


def test_regen_distance_is_an_overlay_and_ev_petrol_totals_stay_separate():
    first_ts = "2026-01-01T10:00:00+00:00"
    second_ts = "2026-01-01T10:01:00+00:00"
    session = VehicleSession(
        total_distance_km=8,
        electric_distance_km=5,
        petrol_distance_km=3,
        route_points=[
            _route_point(
                first_ts,
                51.5,
                -0.1,
                {
                    "soc": _signal(50, first_ts, "percent"),
                    "engine_active": _signal(False, first_ts),
                    "altitude_m": _signal(91, first_ts, "m"),
                },
            ),
            _route_point(
                second_ts,
                51.6,
                -0.2,
                {
                    "soc": _signal(51, second_ts, "percent"),
                    "engine_active": _signal(False, second_ts),
                },
            ),
        ],
    )
    serializer = VehicleSessionDetailsSerializer()

    segments = serializer.get_route_segments(session)
    summary = serializer.get_summary(session)
    points = serializer.get_normalized_route_points(session)

    assert [segment["mode"] for segment in segments] == ["EV"]
    assert [segment["is_regen"] for segment in segments] == [True]
    assert points[0]["soc"] == 50
    assert points[0]["soc_ts"] == first_ts
    # assert points[0]["altitude_m"] == 91
    # assert points[0]["altitude_ts"] == first_ts
    assert 11 < segments[0]["distance_km"] < 14
    assert summary["electric_distance_km"] == 5.0
    assert summary["petrol_distance_km"] == 3.0
    assert summary["regen_distance_km"] == segments[0]["distance_km"]
    assert summary["regen_distance_estimated"] is True


def test_route_mode_is_unknown_without_engine_or_range_samples():
    session = VehicleSession(
        route_points=[
            _route_point("2026-01-01T10:00:00+00:00", 51.5, -0.1),
            _route_point("2026-01-01T10:01:00+00:00", 51.6, -0.2),
        ],
    )

    segments = VehicleSessionDetailsSerializer().get_route_segments(session)

    assert [segment["mode"] for segment in segments] == ["UNKNOWN"]


def test_route_mode_uses_trip_split_for_unambiguously_electric_trip():
    session = VehicleSession(
        total_distance_km=3,
        electric_distance_km=3,
        petrol_distance_km=0,
        route_points=[
            _route_point("2026-01-01T10:00:00+00:00", 51.5, -0.1),
            _route_point("2026-01-01T10:01:00+00:00", 51.6, -0.2),
        ],
    )

    segments = VehicleSessionDetailsSerializer().get_route_segments(session)

    assert [segment["mode"] for segment in segments] == ["EV"]


def test_route_mode_uses_electric_range_until_depleted():
    first_ts = "2026-01-01T10:00:00+00:00"
    second_ts = "2026-01-01T10:01:00+00:00"
    third_ts = "2026-01-01T10:02:00+00:00"
    session = VehicleSession(
        total_distance_km=10,
        electric_distance_km=1,
        petrol_distance_km=9,
        route_points=[
            _route_point(
                first_ts,
                51.5,
                -0.1,
                {"electric_range_km": _signal(1, first_ts, "km")},
            ),
            _route_point(
                second_ts,
                51.6,
                -0.2,
                {"electric_range_km": _signal(0, second_ts, "km")},
            ),
            _route_point(
                third_ts,
                51.7,
                -0.3,
                {"electric_range_km": _signal(0, third_ts, "km")},
            ),
        ],
    )

    segments = VehicleSessionDetailsSerializer().get_route_segments(session)

    assert [segment["mode"] for segment in segments] == ["EV", "ICE"]
