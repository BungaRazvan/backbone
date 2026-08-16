from common.mixins import AutoStrMixin
from django.db import models


class VehicleTelemetryLog(AutoStrMixin, models.Model):

    class Meta:
        db_table = "vehicle_telemetry_logs"
        app_label = "mytools"
        ordering = ["-vtl_timestamp"]
        indexes = [models.Index(fields=["vtl_vehicle", "vtl_timestamp"])]

    vtl_timestamp = models.DateTimeField(help_text="UTC timestamp of the telemetry row")

    vtl_vehicle = models.ForeignKey(
        "Vehicle", on_delete=models.CASCADE, related_name="telemetry_logs"
    )

    # Core Telemetry Data
    vtl_odometer_km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Current vehicle odemeter",
    )

    vtl_remaining_electric_range_km = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Last remaining range in km",
    )

    # GPS Coordinates
    vtl_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Location latitude",
    )

    vtl_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Location longitude",
    )
