import datetime

from django.db import models

from common.mixins import AutoStrMixin


class TariffPeriod(AutoStrMixin, models.Model):
    class Meta:
        db_table = "tarif_periods"
        app_label = "mytools"

    tp_provider_name = models.CharField(
        max_length=255, help_text="e.g., Octopus, E.ON, OVO"
    )
    tp_tariff_name = models.CharField(
        max_length=255, help_text="e.g., Intelligent Go, Fixed v1"
    )

    # When this specific tariff contract was/is active
    tp_start_date = models.DateField(help_text="When you started this tariff")
    tp_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Leave blank if this is your current active tariff",
    )

    # Base rates (if you have flat pricing)
    tp_standard_import_rate = models.DecimalField(
        max_digits=6, decimal_places=4, help_text="Cost per kWh imported"
    )
    tp_standard_export_rate = models.DecimalField(
        help_text="Payment per kWh exported", max_digits=6, decimal_places=4
    )
    tp_standing_charge_rate = models.DecimalField(max_digits=6, decimal_places=4)

    # Time-of-Use tracking flags
    tp_has_variable_rates = models.BooleanField(
        default=False, help_text="Check if rates change by hour or day/night"
    )

    @property
    def standing_charge(self):
        if self.tp_end_date:
            days = self.tp_end_date - self.tp_start_date
        else:
            days = self.tp_end_date - datetime.date.today()

        return self.tp_standing_charge_rate * days
