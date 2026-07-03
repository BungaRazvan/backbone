from django.db import models

from common.mixins import AutoStrMixin


class Gas(AutoStrMixin, models.Model):
    class Meta:
        app_label = "mytools"

    g_bill = models.OneToOneField("Bill", on_delete=models.CASCADE, related_name="gas")
    g_kwh_used = models.DecimalField(
        max_digits=10, decimal_places=4, help_text="Energy used in kWh"
    )
    g_unit_rate = models.DecimalField(
        max_digits=7, decimal_places=4, help_text="Rate in Pounds per kWh"
    )
    g_standing_charge_rate = models.DecimalField(
        max_digits=6, decimal_places=4, help_text="Daily charge in Pounds"
    )
    g_standing_charge_total = models.DecimalField(
        max_digits=8, decimal_places=2, help_text="Total standing charge in Pounds"
    )
    g_total_cost = models.DecimalField(
        max_digits=8, decimal_places=2, help_text="Total gas cost in Pounds"
    )
