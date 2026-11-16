from common.mixins import AutoStrMixin

from django.db import models


class Vehicle(AutoStrMixin, models.Model):

    class Meta:
        db_table = "vehicles"
        app_label = "mytools"

    class FuelType(models.TextChoices):
        PETROL = "PETROL", "Petrol"
        DIESEL = "DIESEL", "Diesel"
        BEV = "BEV", "Battery Electric"
        PHEV = "PHEV", "Plug-in Hybrid "
        HYBRID = "HYBRID", "Full Hybrid"

    vin = models.CharField(
        max_length=255,
        unique=True,
        primary_key=True,
    )

    name = models.CharField(max_length=50, blank=True, null=True)
    make = models.CharField(max_length=50, blank=False, null=False)
    model = models.CharField(max_length=50, blank=False, null=False)
    year = models.PositiveIntegerField(blank=True, null=True)

    fuel_type = models.CharField(
        max_length=10,
        choices=FuelType.choices,
        default=FuelType.PHEV,
        help_text="Primary fuel setup (Petrol, Diesel, BEV, PHEV)",
    )

    # Generic ICE & EV Baseline Benchmarks
    baseline_ice_mpg = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Baseline ICE fuel efficiency in MPG (Petrol/Diesel equivalent)",
    )
    baseline_ev_mi_per_kwh = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Baseline EV efficiency in mi/kWh",
    )

    is_active = models.BooleanField(blank=False, null=False, default=True)
