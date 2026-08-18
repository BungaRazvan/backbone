from common.mixins import AutoStrMixin

from django.db import models


class Vehicle(models.Model):

    class Meta:
        db_table = "vehicles"
        app_label = "mytools"

    class FuelType(models.TextChoices):
        PETROL = "PETROL", "Petrol"
        DIESEL = "DIESEL", "Diesel"
        BEV = "BEV", "Battery Electric"
        PHEV = "PHEV", "Plug-in Hybrid "
        HYBRID = "HYBRID", "Full Hybrid"

    v_vin = models.CharField(
        max_length=255,
        unique=True,
        primary_key=True,
    )

    v_name = models.CharField(max_length=50, blank=True, null=True)
    v_make = models.CharField(max_length=50, blank=False, null=False)
    v_model = models.CharField(max_length=50, blank=False, null=False)
    v_year = models.PositiveIntegerField(blank=True, null=True)

    v_fuel_type = models.CharField(
        max_length=10,
        choices=FuelType.choices,
        default=FuelType.PHEV,
        help_text="Primary fuel setup (Petrol, Diesel, BEV, PHEV)",
    )

    # Generic ICE & EV Baseline Benchmarks
    v_baseline_ice_mpg = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Baseline ICE fuel efficiency in MPG (Petrol/Diesel equivalent)",
    )
    v_baseline_ev_mi_per_kwh = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Baseline EV efficiency in mi/kWh",
    )

    v_is_active = models.BooleanField(blank=False, null=False, default=True)
