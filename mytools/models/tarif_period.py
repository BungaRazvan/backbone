from django.db import models


class TariffPeriod(models.Model):
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
    tp_standard_import_rate = models.FloatField(help_text="Cost per kWh imported")
    tp_standard_export_rate = models.FloatField(help_text="Payment per kWh exported")

    # Time-of-Use tracking flags
    tp_has_variable_rates = models.BooleanField(
        default=False, help_text="Check if rates change by hour or day/night"
    )
