from django.db import models
from common.mixins import AutoStrMixin


class VehicleTrip(AutoStrMixin, models.Model):

    class Meta:
        db_table = "vehicle_trips"
        app_label = "mytools"
        ordering = ["-vt_started_at"]

    vt_vehicle = models.ForeignKey(
        "Vehicle",
        on_delete=models.CASCADE,
        related_name="trips",
    )

    vt_started_at = models.DateTimeField()
    vt_ended_at = models.DateTimeField()

    vt_start_log = models.ForeignKey(
        "VehicleTelemetryLog",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trip_starts",
    )

    vt_end_log = models.ForeignKey(
        "VehicleTelemetryLog",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trip_ends",
    )

    vt_distance_miles = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    vt_electric_miles = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    vt_fuel_miles = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )

    vt_net_savings = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
