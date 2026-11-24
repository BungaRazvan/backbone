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
        CHARGE = "CHARGE", "Charging Session"
        UNLOCK = "UNLOCK", "Unlock"
        LOCK = "LOCK", "Lock"
        ACCESS = "ACCESS", "Lock / Unlock / Access"
        OTHER = "OTHER", "Other"

    class ElectricEnergySource(models.TextChoices):
        BMW_REPORTED = "BMW_REPORTED", "BMW-reported trip energy"
        AVG_CONSUMPTION = "AVG_CONSUMPTION", "Estimated from average consumption"
        SOC_CHANGE = "SOC_CHANGE", "Estimated from SOC change"
        SME_ENERGY_DELTA = "SME_ENERGY_DELTA", "Estimated from BMW charging delta"
        LEGACY_UNKNOWN = "LEGACY_UNKNOWN", "Legacy value; source unknown"

    class DistanceSplitSource(models.TextChoices):
        BMW_REPORTED = "BMW_REPORTED", "BMW-reported electric fraction"
        ELECTRIC_RANGE_DROP = (
            "ELECTRIC_RANGE_DROP",
            "Estimated (rough) from remaining electric range",
        )
        SAME_DAY_PATTERN = (
            "SAME_DAY_PATTERN",
            "Estimated from same-day trip pattern",
        )

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
        help_text="Inferred from BMW event signals; a session may include stationary snapshots.",
    )

    started_at = models.DateTimeField(
        db_index=True,
        verbose_name="First event at",
        help_text="Start of the BMW event window, not necessarily when the vehicle began moving.",
    )
    ended_at = models.DateTimeField(
        db_index=True,
        verbose_name="Last event at",
        help_text="End of the BMW event window, not necessarily when the vehicle stopped moving.",
    )
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
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="May be estimated from remaining electric range or same-day trip pattern; check the distance split source.",
    )
    petrol_distance_km = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Calculated as total distance minus electric distance; estimate when the split source is estimated.",
    )
    distance_split_source = models.CharField(
        max_length=24,
        choices=DistanceSplitSource.choices,
        blank=True,
        default="",
        help_text="Indicates whether the electric/petrol distance split is reported or estimated.",
    )
    fuel_consumed_liters = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Calculated from BMW fuel-level readings; blank when unavailable.",
    )
    fuel_level_start_liters = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="First remaining-fuel level reported during this session.",
    )
    fuel_level_end_liters = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Last remaining-fuel level reported during this session.",
    )
    electric_consumed_kwh = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="May be an estimate; check the energy source field.",
    )
    electric_consumed_kwh_source = models.CharField(
        max_length=24,
        choices=ElectricEnergySource.choices,
        blank=True,
        default="",
        help_text="Indicates whether electric energy was reported by BMW or estimated.",
    )
    recuperated_kwh = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Calculated from BMW's recuperation signal and trip distance; blank when unavailable.",
    )
    ice_engine_ran = models.BooleanField(
        default=False,
        help_text="False means combustion was not detected; BMW may not report enough signals to confirm.",
    )

    # SOC values are observations near the event-window edges, not interpolated values.
    start_soc = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="BMW SOC reading within 15 minutes of the first event; blank if none was reported.",
    )
    end_soc = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="BMW SOC reading within 15 minutes of the last event; blank if none was reported.",
    )
    route_points = models.JSONField(
        default=list,
        blank=True,
        help_text="GPS points with provider-neutral route signals and per-signal timestamps.",
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    @property
    def fuel_level_change_liters(self):
        if self.fuel_level_start_liters is None or self.fuel_level_end_liters is None:
            return None
        return self.fuel_level_end_liters - self.fuel_level_start_liters
