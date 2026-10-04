from django.db import models

from common.mixins.auto_str import AutoStrMixin


class AnnualEnergySummary(AutoStrMixin, models.Model):
    class Meta:
        app_label = "mytools"
        db_table = "annual_energy_summarys"

    year = models.PositiveIntegerField(null=False, blank=False)
    last_proccessed_month = models.PositiveSmallIntegerField(null=False, blank=False)

    grid_import_kwh = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=False,
        blank=False,
        help_text="Total grid import in kWh for the year",
    )
    grid_export_kwh = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=False,
        blank=False,
        help_text="Total grid export in kWh for the year",
    )
    home_consumption_kwh = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=False,
        blank=False,
        help_text="Total energy the home consumed",
    )

    total_exported_revenue = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=False,
        blank=False,
        help_text="Total revenue from exported energy for the year",
    )
    savings = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=False,
        blank=False,
        help_text="Total savings for the year",
    )
    total_gross_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=False,
        blank=False,
        help_text="Total estimated cost without solar panels",
    )
    total_net_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=False,
        blank=False,
        help_text="Total cost of the bought energy",
    )
