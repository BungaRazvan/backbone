import dataclasses
import math
from decimal import Decimal
from typing import List, Optional

from django.utils.decorators import method_decorator
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from common.auth.backends import app_auth
from common.auth.decorators import validate_arguments
from mytools.models import VehicleSession

REGEN_SOC_DELTA_PCT = 0.5
EARTH_RADIUS_KM = 6371.0088


class VehicleSessionDetailsSerializer(serializers.ModelSerializer):
    normalized_route_points = serializers.SerializerMethodField()
    route_segments = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()

    class Meta:
        model = VehicleSession
        fields = [
            "id",
            "vehicle_id",
            "activity_type",
            "started_at",
            "ended_at",
            "event_count",
            "start_odometer_km",
            "end_odometer_km",
            "total_distance_km",
            "electric_distance_km",
            "petrol_distance_km",
            "fuel_consumed_liters",
            "electric_consumed_kwh",
            "recuperated_kwh",
            "ice_engine_ran",
            "start_soc",
            "end_soc",
            "merged_state",
            "normalized_route_points",
            "route_segments",
            "summary",
        ]

    def _build_points(self, obj: VehicleSession) -> list[dict]:
        raw = obj.route_points if isinstance(obj.route_points, list) else []
        points: list[dict] = []

        for point in raw:
            if not isinstance(point, dict):
                continue

            signals = point.get("signals")

            if not isinstance(signals, dict):
                signals = {}

            try:
                lat = float(point["lat"])
                lon = float(point["lon"])
            except (KeyError, TypeError, ValueError):
                continue

            soc = signals.get("soc")
            engine_active = signals.get("engine_active")
            electric_range = signals.get("electric_range_km")
            # altitude = signals.get("altitude_m")
            soc = soc if isinstance(soc, dict) else {}
            engine_active = engine_active if isinstance(engine_active, dict) else {}
            electric_range = electric_range if isinstance(electric_range, dict) else {}
            # altitude = altitude if isinstance(altitude, dict) else {}

            points.append(
                {
                    "ts": point.get("ts"),
                    "lat": lat,
                    "lon": lon,
                    "soc": soc.get("value"),
                    "soc_ts": soc.get("ts"),
                    "engine_active": engine_active.get("value"),
                    "electric_range_km": electric_range.get("value"),
                    "electric_range_ts": electric_range.get("ts"),
                    # "altitude_m": altitude.get("value"),
                    # "altitude_ts": altitude.get("ts"),
                }
            )

        return points

    def get_normalized_route_points(self, obj: VehicleSession) -> list[dict]:
        return self._build_points(obj)

    @staticmethod
    def _distance_km(start: dict, end: dict) -> float:
        lat1, lon1 = math.radians(start["lat"]), math.radians(start["lon"])
        lat2, lon2 = math.radians(end["lat"]), math.radians(end["lon"])
        delta_lat = lat2 - lat1
        delta_lon = lon2 - lon1
        haversine = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
        )
        return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(min(1.0, max(0.0, haversine))))

    def get_route_segments(self, obj: VehicleSession) -> list[dict]:
        points = self._build_points(obj)
        segments: list[dict] = []

        for i in range(len(points) - 1):
            p1, p2 = points[i], points[i + 1]

            if p1["lat"] == p2["lat"] and p1["lon"] == p2["lon"]:
                continue

            soc_delta = (
                p2["soc"] - p1["soc"]
                if p1["soc"] is not None
                and p2["soc"] is not None
                and p1["soc_ts"] != p2["soc_ts"]
                else None
            )
            range_delta = (
                p2["electric_range_km"] - p1["electric_range_km"]
                if p1["electric_range_km"] is not None
                and p2["electric_range_km"] is not None
                and p1["electric_range_ts"] != p2["electric_range_ts"]
                else None
            )

            if p1["engine_active"] is not None:
                propulsion_mode = "ICE" if p1["engine_active"] else "EV"
            else:
                propulsion_mode = "UNKNOWN"

                if (
                    obj.total_distance_km is not None
                    and obj.electric_distance_km is not None
                    and obj.petrol_distance_km is not None
                ):
                    if (
                        obj.electric_distance_km == obj.total_distance_km
                        and obj.petrol_distance_km == 0
                    ):
                        propulsion_mode = "EV"
                    elif (
                        obj.petrol_distance_km == obj.total_distance_km
                        and obj.electric_distance_km == 0
                    ):
                        propulsion_mode = "ICE"

                if propulsion_mode == "UNKNOWN" and p1["electric_range_km"] is not None:
                    if p1["electric_range_km"] > 0:
                        propulsion_mode = "EV"
                    elif (
                        obj.petrol_distance_km is not None
                        and obj.petrol_distance_km > 0
                    ):
                        propulsion_mode = "ICE"

            if soc_delta is None and range_delta is None:
                is_regen = None
            else:
                is_regen = (
                    soc_delta is not None and soc_delta >= REGEN_SOC_DELTA_PCT
                ) or (range_delta is not None and range_delta > 0)

            segments.append(
                {
                    "coords": [[p1["lat"], p1["lon"]], [p2["lat"], p2["lon"]]],
                    "mode": propulsion_mode,
                    "is_regen": is_regen,
                    "distance_km": round(self._distance_km(p1, p2), 3),
                    "startPoint": p1,
                    "endPoint": p2,
                }
            )

        return segments

    def get_summary(self, obj: VehicleSession) -> dict:
        total_dist = obj.total_distance_km
        ev_dist = obj.electric_distance_km
        petrol_dist = obj.petrol_distance_km
        route_segments = self.get_route_segments(obj)

        ev_share_pct = None
        if total_dist and total_dist > 0 and ev_dist is not None:
            ev_share_pct = float(
                (
                    Decimal(str(ev_dist)) / Decimal(str(total_dist)) * Decimal("100")
                ).quantize(Decimal("0.1"))
            )

        regen_distance_km = (
            round(
                sum(
                    segment["distance_km"]
                    for segment in route_segments
                    if segment["is_regen"]
                ),
                3,
            )
            if any(segment["is_regen"] is not None for segment in route_segments)
            else None
        )

        duration_seconds = None
        duration_text = None
        if obj.started_at and obj.ended_at:
            secs = max(0, int((obj.ended_at - obj.started_at).total_seconds()))
            duration_seconds = secs
            mins = secs // 60
            hrs, rem_mins = divmod(mins, 60)
            duration_text = f"{hrs}h {rem_mins}m" if hrs else f"{mins}m"

        return {
            "distance_km": float(total_dist) if total_dist is not None else None,
            "electric_distance_km": float(ev_dist) if ev_dist is not None else None,
            "petrol_distance_km": (
                float(petrol_dist) if petrol_dist is not None else None
            ),
            "ev_share_pct": ev_share_pct,
            "regen_distance_km": regen_distance_km,
            "regen_distance_estimated": True,
            "duration_seconds": duration_seconds,
            "duration_text": duration_text,
            "start_soc": float(obj.start_soc) if obj.start_soc is not None else None,
            "end_soc": float(obj.end_soc) if obj.end_soc is not None else None,
            "battery_soc": float(obj.end_soc) if obj.end_soc is not None else None,
            "electric_consumed_kwh": (
                float(obj.electric_consumed_kwh)
                if obj.electric_consumed_kwh is not None
                else None
            ),
            "recuperated_kwh": (
                float(obj.recuperated_kwh) if obj.recuperated_kwh is not None else None
            ),
            "fuel_consumed_liters": (
                float(obj.fuel_consumed_liters)
                if obj.fuel_consumed_liters is not None
                else None
            ),
            "ice_engine_ran": bool(obj.ice_engine_ran),
        }


@dataclasses.dataclass
class ArgsGet:
    id: Optional[int] = None
    ids: Optional[List[int]] = None


class VehicleSessionDetailsView(APIView):
    authentication_classes = [app_auth("mytools")]

    @method_decorator(validate_arguments(ArgsGet))
    def get(self, request, args):
        ids_to_fetch = set()

        if args.id is not None:
            ids_to_fetch.add(args.id)
        if args.ids:
            ids_to_fetch.update(args.ids)

        if not ids_to_fetch:
            return Response(status=400)

        qs = VehicleSession.objects.filter(id__in=ids_to_fetch).order_by(
            "started_at", "id"
        )

        serializer = VehicleSessionDetailsSerializer(qs, many=True)
        return Response(serializer.data)
