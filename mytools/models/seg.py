from django.db import models

from common.mixins import AutoStrMixin


class Seg(AutoStrMixin, models.Model):
    class Meta:
        app_label = "mytools"

    s_bill = models.OneToOneField("Bill", on_delete=models.CASCADE, related_name="seg")
    s_kwh_exported = models.DecimalField(
        max_digits=10, decimal_places=4, help_text="Energy used in kWh"
    )
    s_export_rate = models.DecimalField(
        max_digits=7, decimal_places=4, help_text="Export rate in Pounds per kWh"
    )

    s_total_credit = models.DecimalField(
        max_digits=8, decimal_places=2, help_text="Total credit generated in Pounds"
    )
