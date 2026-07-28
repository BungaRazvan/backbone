from django.db import models

from common.mixins import AutoStrMixin


class ChargePointHistory(AutoStrMixin, models.Model):
    class Meta:
        db_table = "charge_point_history"
        app_label = "mytools"

    cph_import_tariff = models.ForeignKey(
        "mytools.TariffPeriod",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="import_charge_sessions",
        help_text="The Import Tariff active during this session",
    )
    cph_export_tariff = models.ForeignKey(
        "mytools.TariffPeriod",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="export_charge_sessions",
        help_text="The SEG / Export Tariff active during this session",
    )

    cph_kwh = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        blank=False,
        null=False,
        help_text="kWh charged",
    )
    cph_solar_kwh = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        blank=True,
        null=True,
        help_text="Estimated kWh supplied by solar panels",
    )
    cph_grid_kwh = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        blank=True,
        null=True,
        help_text="Estimated kWh imported from grid",
    )
    cph_battery_kwh = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        blank=True,
        null=True,
        help_text="kWh supplied to EV via home battery discharge",
    )
    cph_start_meter_kwh = models.DecimalField(
        max_digits=20, decimal_places=8, blank=False, null=False
    )
    cph_end_meter_kwh = models.DecimalField(
        max_digits=20, decimal_places=8, blank=False, null=False
    )
    cph_net_cost = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        blank=True,
        null=True,
        help_text="Actual out-of-pocket cost for this charge session after self-generation/credits (£)",
    )
    cph_feed_in_loss = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        blank=True,
        null=True,
        help_text="Opportunity cost of using self-generated energy instead of exporting via SEG (£)",
    )
    cph_gross_cost = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        blank=True,
        null=True,
        help_text="Cost if 100% of charge came from grid",
    )

    cph_started_at = models.DateTimeField(blank=False, null=False)
    cph_completed_at = models.DateTimeField(blank=False, null=False)
    cph_created_at = models.DateTimeField(blank=False, null=False)

    cph_state = models.CharField(blank=False, null=False, max_length=255)

    @property
    def solar_savings(self) -> float:
        """Money saved by charging with solar instead of full grid power."""

        if self.cph_gross_cost is not None and self.cph_net_cost is not None:
            return float(self.cph_gross_cost - self.cph_net_cost)

        return 0.0
