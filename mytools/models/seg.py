from django.db import models

from common.mixins import AutoStrMixin


class Seg(AutoStrMixin, models.Model):
    class Meta:
        app_label = "mytools"
        db_table = "seg"

    s_bill = models.OneToOneField("Bill", on_delete=models.CASCADE, related_name="seg")

    s_from_date = models.DateField()
    s_to_date = models.DateField()

    s_kwh_used = models.DecimalField(
        max_digits=10, decimal_places=4, help_text="Energy used in kWh"
    )
    s_unit_rate = models.DecimalField(
        max_digits=7, decimal_places=4, help_text="Export rate in Pounds per kWh"
    )

    s_total_cost = models.DecimalField(
        max_digits=8, decimal_places=2, help_text="Total credit generated in Pounds"
    )
