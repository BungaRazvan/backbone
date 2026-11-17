from django.db import models
from common.mixins import AutoStrMixin


class VehicleSession(AutoStrMixin, models.Model):
    class Meta:
        db_table = "vehicle_sessions"
        app_label = "mytools"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["vehicle", "activity_type", "-started_at"]),
        ]

    class ActivityType(models.TextChoices):
        DRIVE = "DRIVE", "Drive / Trip"
        ACCESS = "ACCESS", "Lock / Unlock / Access"
        CHARGE = "CHARGE", "Charging Session"
        OTHER = "OTHER", "Status Heartbeat"

    vehicle = models.ForeignKey(
        "mytools.Vehicle",
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    activity_type = models.CharField(
        max_length=12,
        choices=ActivityType.choices,
        default=ActivityType.OTHER,
        db_index=True,
    )

    # Time window of the merged cluster
    started_at = models.DateTimeField(db_index=True)
    ended_at = models.DateTimeField(db_index=True)
    event_count = models.PositiveIntegerField(default=0)

    # Merged latest-known state snapshot across all events in this session
    merged_state = models.JSONField(
        default=dict,
        help_text="Flattened key->latest_value map merged from all events in this session",
    )

    # Driving-specific metrics (populated when activity_type == DRIVE)
    start_odometer_km = models.DecimalField(
        max_digits=9, decimal_places=1, null=True, blank=True
    )
    end_odometer_km = models.DecimalField(
        max_digits=9, decimal_places=1, null=True, blank=True
    )
    total_distance_km = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    electric_distance_km = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    fuel_consumed_liters = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    electric_consumed_kwh = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    recuperated_kwh = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    ice_engine_ran = models.BooleanField(default=False)

    # Battery & GPS snapshots (useful for both DRIVE and CHARGE)
    start_soc = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    end_soc = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    route_points = models.JSONField(
        default=list,
        blank=True,
        help_text="Ordered list of [timestamp, lat, lon, soc] points during a drive",
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
